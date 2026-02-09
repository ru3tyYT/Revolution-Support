"""Knowledge base Discord cog.

Provides commands for managing knowledge base documents and searching.
"""

import io
import uuid
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button
from sqlalchemy.orm import Session

from database.connection import get_db_context
from database.models import KnowledgeDoc, KnowledgeChunk
from knowledge.chunker import TextChunker, ChunkConfig
from knowledge.rag import RAGSystem, RAGConfig
from knowledge.search import KnowledgeSearch
from ai.embeddings import get_embedding_generator


class KnowledgeModal(Modal):
    """Modal for adding/editing knowledge documents."""

    def __init__(self, title: str, doc_id: Optional[str] = None, content: str = ""):
        super().__init__(title=title)
        self.doc_id = doc_id

        self.content_input = TextInput(
            label="Content",
            style=discord.TextStyle.paragraph,
            placeholder="Enter the document content here...",
            default=content,
            required=True,
            max_length=4000,
        )
        self.add_item(self.content_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)


class KnowledgeCog(commands.Cog):
    """Knowledge base management commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.chunker = TextChunker(ChunkConfig(chunk_size=1000, chunk_overlap=200))

    def _create_embed(
        self,
        title: str,
        description: str = "",
        color: discord.Color = discord.Color.blue(),
    ) -> discord.Embed:
        """Create a standardized embed."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(
            text="Knowledge Base", icon_url=self.bot.user.display_avatar.url
        )
        return embed

    async def _process_document(
        self,
        title: str,
        content: str,
        guild_id: int,
        created_by: int,
        doc_type: str = "text",
    ) -> KnowledgeDoc:
        """Process and store a document with chunks."""
        with get_db_context() as db:
            # Create document
            doc = KnowledgeDoc(
                id=uuid.uuid4(),
                guild_id=guild_id,
                title=title,
                content=content,
                doc_type=doc_type,
                created_by=created_by,
            )
            db.add(doc)
            db.flush()

            # Chunk content
            chunks = self.chunker.chunk_text(content)

            # Generate embeddings and create chunks
            if chunks:
                generator = get_embedding_generator()
                chunk_texts = [chunk.content for chunk in chunks]
                embeddings = await generator.generate_batch(chunk_texts)

                for i, (chunk_data, embedding) in enumerate(zip(chunks, embeddings)):
                    chunk = KnowledgeChunk(
                        id=uuid.uuid4(),
                        document_id=doc.id,
                        chunk_index=i,
                        content=chunk_data.content,
                        token_count=chunk_data.token_count,
                        embedding=embedding,
                    )
                    db.add(chunk)

            db.commit()
            return doc

    @app_commands.command(name="knowledge", description="Knowledge base management")
    @app_commands.describe(
        action="Action to perform",
        title_or_id="Document title or ID",
        query="Search query",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="add", value="add"),
            app_commands.Choice(name="edit", value="edit"),
            app_commands.Choice(name="remove", value="remove"),
            app_commands.Choice(name="list", value="list"),
            app_commands.Choice(name="search", value="search"),
            app_commands.Choice(name="view", value="view"),
        ]
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def knowledge(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        title_or_id: Optional[str] = None,
        query: Optional[str] = None,
    ):
        """Knowledge base management command."""
        if action.value == "add":
            if not title_or_id:
                await interaction.response.send_message(
                    embed=self._create_embed(
                        "Error",
                        "Please provide a title for the document.",
                        discord.Color.red(),
                    ),
                    ephemeral=True,
                )
                return

            # Show modal for content input
            modal = KnowledgeModal(f"Add Document: {title_or_id}")
            await interaction.response.send_modal(modal)

            # Wait for modal submission
            try:
                await modal.wait()
                content = modal.content_input.value

                # Process document
                doc = await self._process_document(
                    title=title_or_id,
                    content=content,
                    guild_id=interaction.guild_id,
                    created_by=interaction.user.id,
                )

                embed = self._create_embed(
                    "Document Added",
                    f"**Title:** {doc.title}\n**ID:** `{doc.id}`\n**Chunks:** {len(content) // 1000 + 1}",
                    discord.Color.green(),
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.followup.send(
                    embed=self._create_embed(
                        "Error",
                        f"Failed to add document: {str(e)}",
                        discord.Color.red(),
                    ),
                    ephemeral=True,
                )

        elif action.value == "edit":
            if not title_or_id:
                await interaction.response.send_message(
                    embed=self._create_embed(
                        "Error",
                        "Please provide a document ID to edit.",
                        discord.Color.red(),
                    ),
                    ephemeral=True,
                )
                return

            with get_db_context() as db:
                doc = (
                    db.query(KnowledgeDoc)
                    .filter(
                        KnowledgeDoc.id == title_or_id,
                        KnowledgeDoc.guild_id == interaction.guild_id,
                    )
                    .first()
                )

                if not doc:
                    await interaction.response.send_message(
                        embed=self._create_embed(
                            "Error",
                            "Document not found.",
                            discord.Color.red(),
                        ),
                        ephemeral=True,
                    )
                    return

                # Show modal with existing content
                modal = KnowledgeModal(
                    f"Edit Document: {doc.title}", str(doc.id), doc.content
                )
                await interaction.response.send_modal(modal)

                try:
                    await modal.wait()
                    new_content = modal.content_input.value

                    # Update document
                    doc.content = new_content
                    doc.updated_at = discord.utils.utcnow()

                    # Delete old chunks
                    db.query(KnowledgeChunk).filter(
                        KnowledgeChunk.document_id == doc.id,
                    ).delete()

                    # Create new chunks
                    chunks = self.chunker.chunk_text(new_content)
                    if chunks:
                        generator = get_embedding_generator()
                        chunk_texts = [chunk.content for chunk in chunks]
                        embeddings = await generator.generate_batch(chunk_texts)

                        for i, (chunk_data, embedding) in enumerate(
                            zip(chunks, embeddings)
                        ):
                            chunk = KnowledgeChunk(
                                id=uuid.uuid4(),
                                document_id=doc.id,
                                chunk_index=i,
                                content=chunk_data.content,
                                token_count=chunk_data.token_count,
                                embedding=embedding,
                            )
                            db.add(chunk)

                    db.commit()

                    embed = self._create_embed(
                        "Document Updated",
                        f"**Title:** {doc.title}\n**ID:** `{doc.id}`",
                        discord.Color.green(),
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)

                except Exception as e:
                    await interaction.followup.send(
                        embed=self._create_embed(
                            "Error",
                            f"Failed to update document: {str(e)}",
                            discord.Color.red(),
                        ),
                        ephemeral=True,
                    )

        elif action.value == "remove":
            if not title_or_id:
                await interaction.response.send_message(
                    embed=self._create_embed(
                        "Error",
                        "Please provide a document ID to remove.",
                        discord.Color.red(),
                    ),
                    ephemeral=True,
                )
                return

            with get_db_context() as db:
                doc = (
                    db.query(KnowledgeDoc)
                    .filter(
                        KnowledgeDoc.id == title_or_id,
                        KnowledgeDoc.guild_id == interaction.guild_id,
                    )
                    .first()
                )

                if not doc:
                    await interaction.response.send_message(
                        embed=self._create_embed(
                            "Error",
                            "Document not found.",
                            discord.Color.red(),
                        ),
                        ephemeral=True,
                    )
                    return

                title = doc.title
                doc_id = doc.id

                # Delete document (cascades to chunks)
                db.delete(doc)
                db.commit()

                embed = self._create_embed(
                    "Document Removed",
                    f"**Title:** {title}\n**ID:** `{doc_id}`",
                    discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action.value == "list":
            with get_db_context() as db:
                docs = (
                    db.query(KnowledgeDoc)
                    .filter(
                        KnowledgeDoc.guild_id == interaction.guild_id,
                        KnowledgeDoc.is_active == True,
                    )
                    .order_by(KnowledgeDoc.updated_at.desc())
                    .limit(25)
                    .all()
                )

                if not docs:
                    embed = self._create_embed(
                        "Knowledge Base",
                        "No documents found. Use `/knowledge add <title>` to add one.",
                    )
                else:
                    description = []
                    for doc in docs:
                        updated = (
                            doc.updated_at.strftime("%Y-%m-%d %H:%M")
                            if doc.updated_at
                            else "Never"
                        )
                        description.append(
                            f"• `{doc.id}` **{doc.title}** (Updated: {updated})"
                        )

                    embed = self._create_embed(
                        "Knowledge Base Documents",
                        "\n".join(description)
                        if description
                        else "No documents found.",
                    )

                await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action.value == "search":
            if not query:
                await interaction.response.send_message(
                    embed=self._create_embed(
                        "Error",
                        "Please provide a search query.",
                        discord.Color.red(),
                    ),
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True)

            try:
                with get_db_context() as db:
                    search = KnowledgeSearch(db, get_embedding_generator())

                    # Generate embedding
                    generator = get_embedding_generator()
                    query_embedding = await generator.generate(query)

                    # Search
                    results = search.vector_search(
                        query_embedding=query_embedding,
                        guild_id=interaction.guild_id,
                        top_k=5,
                    )

                    if not results:
                        embed = self._create_embed(
                            "Search Results",
                            "No results found for your query.",
                        )
                    else:
                        description = []
                        for i, (chunk, doc, similarity) in enumerate(results[:5], 1):
                            similarity_pct = int(similarity * 100)
                            preview = (
                                chunk.content[:200] + "..."
                                if len(chunk.content) > 200
                                else chunk.content
                            )
                            description.append(
                                f"**{i}.** {doc.title} ({similarity_pct}% match)\n"
                                f"> {preview}\n"
                                f"`ID: {doc.id}`"
                            )

                        embed = self._create_embed(
                            f"Search Results for: {query}",
                            "\n\n".join(description),
                        )
                        embed.set_footer(text=f"Found {len(results)} results")

                    await interaction.followup.send(embed=embed, ephemeral=True)

            except Exception as e:
                await interaction.followup.send(
                    embed=self._create_embed(
                        "Error",
                        f"Search failed: {str(e)}",
                        discord.Color.red(),
                    ),
                    ephemeral=True,
                )

        elif action.value == "view":
            if not title_or_id:
                await interaction.response.send_message(
                    embed=self._create_embed(
                        "Error",
                        "Please provide a document ID to view.",
                        discord.Color.red(),
                    ),
                    ephemeral=True,
                )
                return

            with get_db_context() as db:
                doc = (
                    db.query(KnowledgeDoc)
                    .filter(
                        KnowledgeDoc.id == title_or_id,
                        KnowledgeDoc.guild_id == interaction.guild_id,
                    )
                    .first()
                )

                if not doc:
                    await interaction.response.send_message(
                        embed=self._create_embed(
                            "Error",
                            "Document not found.",
                            discord.Color.red(),
                        ),
                        ephemeral=True,
                    )
                    return

                content_preview = (
                    doc.content[:2000] + "..."
                    if len(doc.content) > 2000
                    else doc.content
                )

                embed = self._create_embed(
                    f"Document: {doc.title}",
                    content_preview,
                )
                embed.add_field(name="ID", value=f"`{doc.id}`", inline=True)
                embed.add_field(name="Type", value=doc.doc_type, inline=True)
                embed.add_field(
                    name="Created",
                    value=doc.created_at.strftime("%Y-%m-%d %H:%M")
                    if doc.created_at
                    else "Unknown",
                    inline=True,
                )

                chunks_count = (
                    db.query(KnowledgeChunk)
                    .filter(
                        KnowledgeChunk.document_id == doc.id,
                    )
                    .count()
                )
                embed.add_field(name="Chunks", value=str(chunks_count), inline=True)

                await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="knowledge_upload", description="Upload a file to knowledge base"
    )
    @app_commands.describe(
        file="File to upload (txt, md, json)",
        title="Document title (optional, uses filename if not provided)",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def knowledge_upload(
        self,
        interaction: discord.Interaction,
        file: discord.Attachment,
        title: Optional[str] = None,
    ):
        """Upload a file to the knowledge base."""
        await interaction.response.defer(ephemeral=True)

        # Validate file
        allowed_extensions = {".txt", ".md", ".json", ".py", ".js", ".html", ".css"}
        file_ext = (
            "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
        )

        if file_ext not in allowed_extensions:
            await interaction.followup.send(
                embed=self._create_embed(
                    "Error",
                    f"File type not supported. Allowed: {', '.join(allowed_extensions)}",
                    discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        # Check file size (max 1MB)
        if file.size > 1024 * 1024:
            await interaction.followup.send(
                embed=self._create_embed(
                    "Error",
                    "File too large. Maximum size is 1MB.",
                    discord.Color.red(),
                ),
                ephemeral=True,
            )
            return

        try:
            # Download file
            content_bytes = await file.read()
            content = content_bytes.decode("utf-8")

            doc_title = title or file.filename
            doc_type = "markdown" if file_ext == ".md" else "text"

            # Process document
            doc = await self._process_document(
                title=doc_title,
                content=content,
                guild_id=interaction.guild_id,
                created_by=interaction.user.id,
                doc_type=doc_type,
            )

            embed = self._create_embed(
                "File Uploaded",
                f"**Title:** {doc.title}\n**ID:** `{doc.id}`\n**Size:** {len(content):,} characters",
                discord.Color.green(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(
                embed=self._create_embed(
                    "Error",
                    f"Failed to upload file: {str(e)}",
                    discord.Color.red(),
                ),
                ephemeral=True,
            )

    @app_commands.command(
        name="ask", description="Ask a question using the knowledge base"
    )
    @app_commands.describe(question="Your question")
    async def ask(
        self,
        interaction: discord.Interaction,
        question: str,
    ):
        """Ask a question using RAG."""
        await interaction.response.defer()

        try:
            with get_db_context() as db:
                rag = RAGSystem(db, RAGConfig(top_k=5, max_context_tokens=2000))

                # Assemble context
                context = await rag.assemble_context(
                    query=question,
                    guild_id=interaction.guild_id,
                )

                if not context.results:
                    embed = self._create_embed(
                        "No Results",
                        "I couldn't find any relevant information to answer your question.",
                        discord.Color.orange(),
                    )
                    await interaction.followup.send(embed=embed)
                    return

                # Build response embed
                embed = self._create_embed(
                    f"Q: {question}",
                    "Here are the most relevant sources I found:",
                )

                for i, result in enumerate(context.results[:3], 1):
                    similarity = int(result.similarity * 100)
                    preview = (
                        result.content[:300] + "..."
                        if len(result.content) > 300
                        else result.content
                    )
                    embed.add_field(
                        name=f"{i}. {result.title} ({similarity}% match)",
                        value=preview,
                        inline=False,
                    )

                if context.sources:
                    source_list = " | ".join(
                        [f"[{s['title']}]" for s in context.sources[:3]]
                    )
                    embed.add_field(
                        name="Sources",
                        value=source_list,
                        inline=False,
                    )

                embed.set_footer(
                    text=f"Search took {context.search_time_ms}ms | {len(context.results)} results",
                )

                await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                embed=self._create_embed(
                    "Error",
                    f"Failed to process question: {str(e)}",
                    discord.Color.red(),
                ),
            )


async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    await bot.add_cog(KnowledgeCog(bot))
