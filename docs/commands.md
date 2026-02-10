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

The bot uses slash commands (`/command`) for the best user experience.

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

Check bot latency and connection status.

**Usage:**
```
/ping
```

**Response:**
- WebSocket Latency (Discord API)
- Message Latency (response time)
- API Latency
- System CPU and RAM usage
- Shard information

**Example Response:**
```
🟢 Pong!
📡 WebSocket Latency: 45ms
💬 Message Latency: 52ms
🌐 API Latency: 45ms
💻 System: CPU 12.5% | RAM 45.2%
```

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

Ask a question using the knowledge base.

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
- Top relevant sources from knowledge base
- Similarity scores for each result
- Document titles and previews
- Search execution time

**Permissions:** Everyone

## Knowledge Base Commands

Commands for searching and managing knowledge base documents.

### `/knowledge`

Knowledge base management with subcommands.

**Usage:**
```
/knowledge action:<action> [parameters]
```

**Actions:**

#### `action:search`

Search the knowledge base.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | Search query |

**Examples:**
```
/knowledge action:search query:password reset
/knowledge action:search query:API authentication
```

**Response:**
- Top 5 matching documents
- Relevance scores
- Document previews
- Links to full documents

**Permissions:** Everyone

#### `action:add`

Add a document to the knowledge base.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| title | string | Yes | Document title |
| content | string | Yes | Document content |

**Permissions:** Manage Guild

#### `action:list`

List all knowledge base documents.

**Response:**
- Document list with IDs
- Last updated timestamps
- Document types

**Permissions:** Manage Guild

---

### `/knowledge_upload`

Upload a file to the knowledge base.

**Usage:**
```
/knowledge_upload file:<attachment> [title:<document title>]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | Attachment | Yes | File to upload (txt, md, json, py, js, html, css) |
| title | string | No | Document title (uses filename if not provided) |

**Supported File Types:**
- `.txt` - Text files
- `.md` - Markdown files
- `.json` - JSON files
- `.py` - Python files
- `.js` - JavaScript files
- `.html` - HTML files
- `.css` - CSS files

**Max File Size:** 1MB

**Examples:**
```
/knowledge_upload file:guide.md
/knowledge_upload file:api-docs.txt title:"API Documentation"
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

## Settings Commands

Commands for configuring bot settings.

### `/settings view`

View current bot settings.

**Usage:**
```
/settings view
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

### `/disable`

Disable the bot in the current channel.

**Usage:**
```
/disable [duration:<duration>]
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| duration | string | No | Duration to disable (e.g., '30m', '2h', '1d'). If not specified, disabled indefinitely. |

**Duration Format:**
- `30m` or `30 minutes` - 30 minutes
- `2h` or `2 hours` - 2 hours
- `1d` or `1 day` - 1 day

**Examples:**
```
/disable
/disable duration:30m
/disable duration:2h
```

**Permissions:** Manage Channels

---

### `/enable`

Re-enable the bot in the current channel.

**Usage:**
```
/enable
```

**Permissions:** Manage Channels

---

### `/disable-ai`

Disable AI responses in the current channel (commands still work).

**Usage:**
```
/disable-ai
```

**What gets disabled:**
- AI-generated responses
- Smart suggestions
- Auto-responses

**What still works:**
- All `/` commands
- Manual commands
- Search functionality

**Permissions:** Manage Channels

---

### `/enable-ai`

Re-enable AI responses in the current channel.

**Usage:**
```
/enable-ai
```

**Permissions:** Manage Channels

## Research Commands

Commands for advanced research and analysis.

### `/research`

Perform a web search with AI analysis.

**Usage:**
```
/research query:<search terms> [depth:basic/detailed/comprehensive]
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| query | string | Yes | - | Search query |
| depth | choice | No | detailed | Research depth level |

**Examples:**
```
/research query:"Python async best practices"
/research query:"Discord API rate limits" depth:comprehensive
```

**Permissions:** Everyone

---

### `/research_status`

Check the status of a research task.

**Usage:**
```
/research_status task_id:<task ID>
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| task_id | string | Yes | The task ID to check |

**Status Values:**
- `⏳ PENDING` - Task is queued
- `🔄 STARTED` - Task has started
- `📊 PROGRESS` - Task is in progress (with progress bar)
- `✅ SUCCESS` - Task completed successfully
- `❌ FAILURE` - Task failed
- `🚫 REVOKED` - Task was cancelled

**Examples:**
```
/research_status task_id:abc123-def456
```

**Permissions:** Everyone

---

### `/research_queue`

View the current research task queue.

**Usage:**
```
/research_queue
```

**Response:**
- 🔄 Active tasks count
- ⏳ Scheduled tasks count
- 📦 Reserved tasks count
- Your active tasks (up to 5)

**Permissions:** Everyone

---

### `/research_cancel`

Cancel a research task.

**Usage:**
```
/research_cancel task_id:<task ID>
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| task_id | string | Yes | The task ID to cancel |

**Notes:**
- You can only cancel your own tasks unless you have Administrator permission
- Tasks that have already completed cannot be cancelled

**Examples:**
```
/research_cancel task_id:abc123-def456
```

**Permissions:** Everyone (own tasks), Administrator (any task)

---

### `/research_compare`

Compare multiple items with research.

**Usage:**
```
/research_compare items:<item1,item2> [criteria:<criterion1,criterion2>]
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| items | string | Yes | - | Comma-separated list of items to compare |
| criteria | string | No | price,features,quality | Comma-separated comparison criteria |

**Examples:**
```
/research_compare items:"Python,JavaScript,Go"
/research_compare items:"AWS,GCP,Azure" criteria:"price,performance,features"
/research_compare items:"React,Vue,Angular" criteria:"learning_curve,performance,ecosystem"
```

**Response:**
- Items compared count
- Rankings with scores
- Recommendation (best option)
- Detailed comparison results

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
| `/stats` | ✅ | ✅ | ✅ | ✅ |
| `/ask` | ✅ | ✅ | ✅ | ✅ |
| `/knowledge action:search` | ✅ | ✅ | ✅ | ✅ |
| `/knowledge action:add` | ❌ | ❌ | ✅ | ✅ |
| `/knowledge action:list` | ❌ | ❌ | ✅ | ✅ |
| `/knowledge_upload` | ❌ | ❌ | ✅ | ✅ |
| `/forum setup` | ❌ | ❌ | ❌ | ✅ |
| `/settings view` | ❌ | ❌ | ❌ | ✅ |
| `/disable` | ❌ | ❌ | ✅* | ✅ |
| `/enable` | ❌ | ❌ | ✅* | ✅ |
| `/disable-ai` | ❌ | ❌ | ✅* | ✅ |
| `/enable-ai` | ❌ | ❌ | ✅* | ✅ |
| `/admin maintenance` | ❌ | ❌ | ❌ | ✅ |
| `/admin system` | ❌ | ❌ | ❌ | ✅ |
| `/admin reload` | ❌ | ❌ | ❌ | ✅ |
| `/research` | ✅ | ✅ | ✅ | ✅ |
| `/research_status` | ✅ | ✅ | ✅ | ✅ |
| `/research_queue` | ✅ | ✅ | ✅ | ✅ |
| `/research_cancel` | ✅** | ✅** | ✅** | ✅ |
| `/research_compare` | ✅ | ✅ | ✅ | ✅ |

\* Requires Manage Channels permission
\** Can only cancel own tasks (Administrators can cancel any task)

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
