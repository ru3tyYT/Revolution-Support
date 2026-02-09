# Command Reference

Complete reference for all Discord Support Bot commands.

## Table of Contents

- [Command Overview](#command-overview)
- [General Commands](#general-commands)
- [Support Commands](#support-commands)
- [Knowledge Base Commands](#knowledge-base-commands)
- [Forum Commands](#forum-commands)
- [Settings Commands](#settings-commands)
- [Admin Commands](#admin-commands)
- [Research Commands](#research-commands)
- [Permission Requirements](#permission-requirements)

## Command Overview

The bot supports both slash commands (`/command`) and legacy prefix commands (`!command`). Slash commands are recommended for the best user experience.

## General Commands

Commands available to all users.

### `/help`

Display help information about bot commands.

**Usage:**
```
/help [command]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| command | string | No | Specific command to get help for |

**Examples:**
```
/help
/help ask
/help forum
```

**Permissions:** Everyone

---

### `/ping`

Check bot latency and status.

**Usage:**
```
/ping
```

**Response:**
```
🏓 Pong!
Latency: 45ms
WebSocket: 32ms
Uptime: 2 days, 4 hours
```

**Permissions:** Everyone

---

### `/status`

Display detailed bot status information.

**Usage:**
```
/status
```

**Response Fields:**
- Bot status and version
- Active connections
- AI provider status
- Database status
- Cache status

**Permissions:** Everyone

---

### `/stats`

Display usage statistics.

**Usage:**
```
/stats [period]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| period | string | No | Time period (today/week/month/all) |

**Permissions:** Everyone

## Support Commands

Commands for requesting and managing support.

### `/ask`

Ask a question to the AI support system.

**Usage:**
```
/ask question:<your question>
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| question | string | Yes | Your question for the AI |

**Examples:**
```
/ask How do I reset my password?
/ask What are the API rate limits?
```

**Response:**
- AI-generated answer
- Sources used (from knowledge base)
- Confidence score
- Response time

**Permissions:** Everyone

---

### `/ticket create`

Create a support ticket.

**Usage:**
```
/ticket create issue:<description> [priority:low/medium/high/urgent]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| issue | string | Yes | Description of the issue |
| priority | choice | No | Ticket priority level |

**Examples:**
```
/ticket create issue:Can't access my account
/ticket create issue:API returning 500 errors priority:high
```

**Permissions:** Everyone

---

### `/ticket view`

View your active tickets.

**Usage:**
```
/ticket view [ticket_id]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| ticket_id | string | No | Specific ticket to view |

**Permissions:** Everyone

---

### `/ticket close`

Close a support ticket.

**Usage:**
```
/ticket close ticket_id:<ticket_id> [reason:<reason>]
```

**Permissions:** Everyone (own tickets), Support Team (any ticket)

---

### `/escalate`

Escalate a conversation to human support.

**Usage:**
```
/escalate [reason:<reason>]
```

**Permissions:** Everyone

---

### `/resolve`

Mark a ticket or thread as resolved.

**Usage:**
```
/resolve [thread:<thread>]
```

**Permissions:** Everyone (own threads), Support Team (any thread)

## Knowledge Base Commands

Commands for searching and managing knowledge base documents.

### `/knowledge search`

Search the knowledge base.

**Usage:**
```
/knowledge search query:<search terms>
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | Search query |

**Examples:**
```
/knowledge search password reset
/knowledge search API authentication
```

**Response:**
- Top 5 matching documents
- Relevance scores
- Document previews
- Links to full documents

**Permissions:** Everyone

---

### `/knowledge add`

Add a document to the knowledge base.

**Usage:**
```
/knowledge add title:<title> content:<content>
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| title | string | Yes | Document title |
| content | string | Yes | Document content |

**Permissions:** Manage Guild

---

### `/knowledge_upload`

Upload a file to the knowledge base.

**Usage:**
```
/knowledge_upload file:<attachment> [title:<title>]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | attachment | Yes | File to upload (.txt, .md, .json, .py, .js, .html, .css) |
| title | string | No | Document title (defaults to filename) |

**Examples:**
```
/knowledge_upload file:api-docs.md
/knowledge_upload file:faq.txt title:"Frequently Asked Questions"
```

**Supported File Types:**
- `.txt` - Plain text
- `.md` - Markdown
- `.json` - JSON files
- `.py` - Python files
- `.js` - JavaScript files
- `.html` - HTML files
- `.css` - CSS files

**File Size Limit:** 1 MB

**Permissions:** Manage Guild

---

### `/knowledge list`

List all knowledge base documents.

**Usage:**
```
/knowledge list
```

**Response:**
- Document list with IDs
- Last updated timestamps
- Document types

**Permissions:** Manage Guild

---

### `/knowledge view`

View a specific knowledge base document.

**Usage:**
```
/knowledge view document_id:<id>
```

**Permissions:** Manage Guild

---

### `/knowledge remove`

Remove a document from the knowledge base.

**Usage:**
```
/knowledge remove document_id:<id>
```

**Permissions:** Manage Guild

---

### `/knowledge edit`

Edit an existing knowledge base document.

**Usage:**
```
/knowledge edit document_id:<id> content:<new content>
```

**Permissions:** Manage Guild

## Forum Commands

Commands for configuring forum channel monitoring.

### `/forum setup`

Configure a forum channel for monitoring.

**Usage:**
```
/forum setup channel:<forum> [auto_respond:true/false] [welcome_message:<text>] [ai_model:<model>] [response_delay:<seconds>] [max_responses:<count>]
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| channel | ForumChannel | Yes | - | Forum to monitor |
| auto_respond | boolean | No | true | Enable automatic AI responses |
| welcome_message | string | No | - | Custom welcome message |
| ai_model | string | No | gpt-4 | AI model to use |
| response_delay | int | No | 5 | Delay before responding (0-300s) |
| max_responses | int | No | 3 | Max AI responses per thread (1-50) |

**Examples:**
```
/forum setup channel:#support-forum
/forum setup channel:#help auto_respond:true ai_model:gpt-4 response_delay:10
```

**Permissions:** Administrator

---

### `/forum edit auto_respond`

Toggle automatic AI responses.

**Usage:**
```
/forum edit auto_respond channel:<forum> enabled:<true/false>
```

**Permissions:** Administrator

---

### `/forum edit welcome_message`

Set the welcome message for new threads.

**Usage:**
```
/forum edit welcome_message channel:<forum> [message:<text>]
```

**Permissions:** Administrator

---

### `/forum edit ai_model`

Change the AI model for responses.

**Usage:**
```
/forum edit ai_model channel:<forum> model:<model choice>
```

**Available Models:**
- GPT-4
- GPT-4 Turbo
- GPT-3.5 Turbo
- Claude 3 Opus
- Claude 3 Sonnet
- Claude 3 Haiku

**Permissions:** Administrator

---

### `/forum edit response_delay`

Set the response delay.

**Usage:**
```
/forum edit response_delay channel:<forum> seconds:<0-300>
```

**Permissions:** Administrator

---

### `/forum edit max_responses`

Set maximum responses per thread.

**Usage:**
```
/forum edit max_responses channel:<forum> count:<1-50>
```

**Permissions:** Administrator

---

### `/forum edit include_tags`

Set tags to monitor (comma-separated).

**Usage:**
```
/forum edit include_tags channel:<forum> [tags:<tag1,tag2>]
```

**Permissions:** Administrator

---

### `/forum edit exclude_tags`

Set tags to exclude.

**Usage:**
```
/forum edit exclude_tags channel:<forum> tags:<tag1,tag2>
```

**Permissions:** Administrator

---

### `/forum enable`

Re-enable monitoring for a forum.

**Usage:**
```
/forum enable channel:<forum>
```

**Permissions:** Administrator

---

### `/forum disable`

Disable monitoring for a forum.

**Usage:**
```
/forum disable channel:<forum>
```

**Permissions:** Administrator

---

### `/forum status`

Show current forum configuration.

**Usage:**
```
/forum status channel:<forum>
```

**Permissions:** Administrator

---

### `/forum list`

List all monitored forums.

**Usage:**
```
/forum list
```

**Permissions:** Administrator

---

### `/forum stats`

Show forum statistics.

**Usage:**
```
/forum stats [channel:<forum>]
```

**Response Fields:**
- Total threads
- AI responses sent
- Resolution rate
- Resolved/closed/active counts

**Permissions:** Administrator

## Settings Commands

Commands for configuring bot settings.

### `/settings view`

View current bot settings.

**Usage:**
```
/settings view
```

**Permissions:** Administrator

---

### `/settings model`

Change the AI model.

**Usage:**
```
/settings model model:<model choice>
```

**Available Models:**
- GPT-4
- GPT-4 Turbo
- GPT-3.5 Turbo
- Claude 3 Opus
- Claude 3 Sonnet
- Claude 3 Haiku

**Permissions:** Administrator

---

### `/settings provider`

Change the AI provider.

**Usage:**
```
/settings provider provider:<provider choice>
```

**Available Providers:**
- OpenAI
- Anthropic
- Google
- Azure OpenAI

**Permissions:** Administrator

---

### `/settings rotate-api-key`

Manually rotate API keys.

**Usage:**
```
/settings rotate-api-key
```

**Permissions:** Administrator

---

### `/settings auto-rotate`

Toggle automatic API key rotation.

**Usage:**
```
/settings auto-rotate state:<on/off>
```

**Permissions:** Administrator

---

### `/settings fallback`

Toggle fallback mode.

**Usage:**
```
/settings fallback state:<on/off>
```

**Permissions:** Administrator

## Admin Commands

Administrative commands for bot management.

### `/admin shard-status`

View shard status (for sharded deployments).

**Usage:**
```
/admin shard-status
```

**Permissions:** Administrator

---

### `/admin maintenance`

Toggle maintenance mode.

**Usage:**
```
/admin maintenance state:<on/off>
```

**Permissions:** Administrator

---

### `/admin logs`

View recent bot logs.

**Usage:**
```
/admin logs
```

**Permissions:** Administrator

---

### `/admin system`

View system information.

**Usage:**
```
/admin system
```

**Response Fields:**
- CPU usage and info
- Memory usage
- Disk usage
- Platform info
- Python version

**Permissions:** Administrator

---

### `/admin reload`

Reload a bot cog (for development).

**Usage:**
```
/admin reload cog:<cog name>
```

**Example:**
```
/admin reload cog:knowledge
```

**Permissions:** Administrator

---

### `/admin costs`

Show cost breakdown and usage.

**Usage:**
```
/admin costs [period:<time period>]
```

**Permissions:** Administrator

---

### `/admin rate-limit`

Set rate limits for a user.

**Usage:**
```
/admin rate-limit user:<@user> seconds:<duration>
```

**Permissions:** Administrator

## Research Commands

Commands for advanced research and analysis.

### `/research search`

Perform a web search with AI analysis.

**Usage:**
```
/research search query:<search terms> [depth:basic/detailed/comprehensive]
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| query | string | Yes | - | Search query |
| depth | choice | No | detailed | Research depth level |

**Examples:**
```
/research search query:"Python async best practices"
/research search query:"Discord API rate limits" depth:comprehensive
```

**Permissions:** Everyone

---

### `/research compare`

Compare multiple items with research.

**Usage:**
```
/research compare items:<item1,item2> criteria:<criterion1,criterion2>
```

**Permissions:** Everyone

---

### `/research analyze`

Analyze a topic or document.

**Usage:**
```
/research analyze content:<text or URL> [type:sentiment/keywords/summary]
```

**Permissions:** Everyone

---

### `/research diagnose`

Diagnose an issue with troubleshooting steps.

**Usage:**
```
/research diagnose problem:<description> [symptoms:<symptom1,symptom2>]
```

**Permissions:** Everyone

## Permission Requirements

### Permission Levels

| Level | Description | Discord Permission |
|-------|-------------|-------------------|
| Everyone | All users | None required |
| Support Team | Support role | Support role or Manage Messages |
| Manage Guild | Server managers | Manage Guild |
| Administrator | Full access | Administrator |
| Bot Owner | Bot owner only | Bot owner ID in config |

### Command Permission Matrix

| Command | Everyone | Support Team | Manage Guild | Administrator |
|---------|----------|--------------|--------------|---------------|
| `/help` | ✅ | ✅ | ✅ | ✅ |
| `/ping` | ✅ | ✅ | ✅ | ✅ |
| `/ask` | ✅ | ✅ | ✅ | ✅ |
| `/ticket create` | ✅ | ✅ | ✅ | ✅ |
| `/knowledge search` | ✅ | ✅ | ✅ | ✅ |
| `/ticket close` | Own | Any | Any | Any |
| `/knowledge add` | ❌ | ❌ | ✅ | ✅ |
| `/knowledge_upload` | ❌ | ❌ | ✅ | ✅ |
| `/forum setup` | ❌ | ❌ | ❌ | ✅ |
| `/settings model` | ❌ | ❌ | ❌ | ✅ |
| `/admin maintenance` | ❌ | ❌ | ❌ | ✅ |

## Legacy Prefix Commands

The bot also supports legacy prefix commands (default prefix: `!`):

```
!help
!ping
!ask <question>
!kb search <query>
!forum monitor <channel>
!config
!stats
```

To change the prefix, set the `BOT_PREFIX` environment variable.

## Command Usage Tips

### Slash Command Autocomplete

Most slash commands support autocomplete for:
- Channel names
- Model names
- Provider names
- Document IDs

Start typing to see suggestions.

### Ephemeral Responses

Many admin commands respond with ephemeral messages (visible only to you). This keeps configuration details private.

### Confirmation Prompts

Destructive actions (like removing documents) will show confirmation prompts to prevent accidents.
