# Docker Build Modes

This project supports two Docker build modes: **local** (for development) and **remote** (for production).

## Quick Start

### Local Development Mode

Build and run from your local code changes:

```bash
make docker-local
```

Or manually:

```bash
cp .env.local .env
docker-compose down
docker-compose up --build
```

### Remote/Production Mode

Pull and run the latest published image from GitHub Container Registry:

```bash
make docker-remote
```

Or manually:

```bash
cp .env.remote .env
docker-compose down
docker-compose pull
docker-compose up
```

## How It Works

The `docker-compose.yml` uses environment variables to control build behavior:

| Variable | Local Mode | Remote Mode | Purpose |
|----------|------------|-------------|---------|
| `DOCKER_IMAGE` | `bankstatementsprocessor` | `ghcr.io/longieirl/bankstatements` | Image name/registry |
| `VERSION` | `local` | `latest` | Image tag |
| `PULL_POLICY` | `build` | `always` | Whether to build or pull |

### Pull Policies

- **`build`**: Always build from local Dockerfile (ignores remote registry)
- **`always`**: Always pull from remote registry (never builds locally)
- **`if_not_present`**: Pull only if image doesn't exist locally
- **`never`**: Never pull, only use local images

## Configuration Files

### `.env.local`
Used for local development. Sets:
- `DOCKER_IMAGE=bankstatementsprocessor` (local image name)
- `VERSION=local` (local tag)
- `PULL_POLICY=build` (always build from source)

### `.env.remote`
Used for production/testing published images. Sets:
- `DOCKER_IMAGE=ghcr.io/longieirl/bankstatements` (registry path)
- `VERSION=latest` (or specific version tag)
- `PULL_POLICY=always` (always pull fresh image)

## Common Workflows

### Development Workflow

1. Make code changes
2. Test locally:
   ```bash
   make docker-local
   ```
3. Verify output in `./output/`

### Testing Published Image

After merging a PR:

1. Switch to remote mode:
   ```bash
   make docker-remote
   ```
2. Verify the published image works correctly

### Using Specific Version

```bash
VERSION=v1.2.3 make docker-remote
```

Or manually:
```bash
DOCKER_IMAGE=ghcr.io/longieirl/bankstatements VERSION=v1.2.3 docker-compose pull
docker-compose up
```

## Troubleshooting

### "Changes not visible in Docker"

Make sure you're in local mode:
```bash
cat .env | grep DOCKER_IMAGE
# Should show: DOCKER_IMAGE=bankstatementsprocessor
```

If it shows the registry path, switch to local:
```bash
make docker-local
```

### "Image not found in registry"

Make sure you're authenticated to GitHub Container Registry:
```bash
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

### Cache Issues

Force rebuild without cache:
```bash
docker-compose build --no-cache
docker-compose up
```

### Clean Start

Remove all containers and images:
```bash
docker-compose down
docker system prune -f
docker-compose up --build
```

## Environment Variables

Both `.env.local` and `.env.remote` can override these application settings:

- `LOG_LEVEL` - Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `ENABLE_DYNAMIC_BOUNDARY` - Smart boundary detection (true/false)
- `SORT_BY_DATE` - Chronological sorting (true/false)
- `OUTPUT_FORMATS` - Output formats (csv, json, excel)
- `GENERATE_MONTHLY_SUMMARY` - Monthly summaries (true/false)
- `TOTALS_COLUMNS` - Columns to calculate totals for

Example custom configuration:
```bash
LOG_LEVEL=DEBUG ENABLE_DYNAMIC_BOUNDARY=false make docker-local
```
