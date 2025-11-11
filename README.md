# Docmost to Outline Migrator

A Python tool to migrate your Docmost exports to Outline, preserving document hierarchy and attachments.

## Features

- ✅ Migrates all documents with proper hierarchy
- ✅ Uploads images and file attachments
- ✅ Converts HTML `<details>` tags to headings (doesn't work 100% of the time)
- ✅ Handles multiple root folders
- ✅ Automatic rate limit handling

⚠️ **Known Limitations:**

- Internal markdown links between documents are not converted
- slashes in document titles may cause issues and are not correctly parsed
   - "Coop/Migros.md" becomes Migros.md
- checkboxes are not imported correctly

## Installation

```bash
# Clone the repository
git clone https://github.com/Raphmatt/docmost2outline.git
cd docmostZip2outline

# Install dependencies
uv sync
```

## Usage

1. Export your Docmost space as a ZIP file
2. Get your Outline API key from Settings ’ API
3. Run the migration:

```bash
python main.py \
  --zip /path/to/export.zip \
  --outline-url https://your-outline.com \
  --api-key your_api_key_here
```

### Options

- `--zip` - Path to Docmost export ZIP file (required)
- `--outline-url` - Your Outline instance URL (required)
- `--api-key` - Outline API key (required)
- `--collection-id` - Use existing collection (optional, creates new if not provided)
- `--max-file-size` - Max file size in MB (default: 25)

## Environment Variables

Alternatively, create a `.env` file:

```bash
cp .env.example .env
```

```env
OUTLINE_URL=https://your-outline.com
OUTLINE_API_KEY=your_api_key_here
```

## License

MIT
