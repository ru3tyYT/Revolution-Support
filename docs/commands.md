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

Check the status of your research request.

**Usage:**
```
/research_status [research_id:<id>]
```

**Permissions:** Everyone

---

### `/research_queue`

View the research queue status.

**Usage:**
```
/research_queue
```

**Permissions:** Everyone

---

### `/research_cancel`

Cancel a pending or in-progress research request.

**Usage:**
```
/research_cancel research_id:<id>
```

**Permissions:** Everyone

---

### `/research_compare`

Compare multiple items with research.

**Usage:**
```
/research_compare items:<item1,item2> criteria:<criterion1,criterion2>
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
| `/stats` | ✅ | ✅ | ✅ | ✅ |
| `/ask` | ✅ | ✅ | ✅ | ✅ |
| `/knowledge action:search` | ✅ | ✅ | ✅ | ✅ |
| `/knowledge action:add` | ❌ | ❌ | ✅ | ✅ |
| `/knowledge action:list` | ❌ | ❌ | ✅ | ✅ |
| `/forum setup` | ❌ | ❌ | ❌ | ✅ |
| `/settings view` | ❌ | ❌ | ❌ | ✅ |
| `/admin maintenance` | ❌ | ❌ | ❌ | ✅ |
| `/admin system` | ❌ | ❌ | ❌ | ✅ |
| `/admin reload` | ❌ | ❌ | ❌ | ✅ |

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
