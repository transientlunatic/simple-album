# GitHub Actions Deployment to DreamHost

This workflow automatically deploys the Simple Album application to your DreamHost server via SSH.

## Setup Instructions

### 1. Generate SSH Key Pair

On your local machine, generate a new SSH key pair for deployment:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f dreamhost-deploy-key
```

This creates two files:
- `dreamhost-deploy-key` (private key)
- `dreamhost-deploy-key.pub` (public key)

### 2. Add Public Key to DreamHost

1. Log into your DreamHost server via SSH
2. Add the public key to your authorized_keys:

```bash
cat dreamhost-deploy-key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 3. Get SSH Host Key Fingerprint

Run this command from your local machine:

```bash
ssh-keyscan -H your-dreamhost-server.dreamhost.com >> known_hosts_temp
cat known_hosts_temp
```

Save the output - you'll need it for the `DREAMHOST_KNOWN_HOSTS` secret.

### 4. Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

#### `DREAMHOST_SSH_KEY`
The contents of your **private key** file (`dreamhost-deploy-key`):
```bash
cat dreamhost-deploy-key
```
Copy the entire output including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`

#### `DREAMHOST_USER`
Your DreamHost SSH username (e.g., `yourusername`)

#### `DREAMHOST_HOST`
Your DreamHost server hostname (e.g., `yourserver.dreamhost.com`)

#### `DREAMHOST_PATH`
The absolute path where the application should be deployed (e.g., `/home/yourusername/yourdomain.com/simple-album`)

#### `DREAMHOST_KNOWN_HOSTS`
The SSH host key from step 3 (the output of `ssh-keyscan`)

### 5. Verify Configuration

After setting up the secrets, you can:

1. **Manual deployment**: Go to Actions → Deploy to DreamHost → Run workflow
2. **Automatic deployment**: Push to the `main` branch

## What the Workflow Does

1. **Checks out the code** from your repository
2. **Sets up SSH authentication** using the private key
3. **Deploys files** via rsync, excluding:
   - Git files and directories
   - Python cache files
   - Virtual environments
   - Test files
   - IDE configuration
   - Local config files
4. **Sets correct file permissions**:
   - Makes dispatch scripts executable (755)
   - Sets application files as readable (644)
   - Creates cache directory (755)
5. **Installs/updates Python dependencies** in a virtual environment

## Security Best Practices

✅ **SSH keys are stored as GitHub Secrets** - never committed to the repository
✅ **Private key has restricted permissions** (600) during deployment
✅ **Known hosts verification** prevents man-in-the-middle attacks
✅ **Minimal permissions** - deploy key only has access to your user account
✅ **Excludes sensitive files** - .gitignore patterns respected

## Troubleshooting

### Deployment fails with "Permission denied"

- Verify the public key is correctly added to `~/.ssh/authorized_keys` on DreamHost
- Check that the private key in `DREAMHOST_SSH_KEY` matches the public key
- Ensure `~/.ssh/authorized_keys` has permissions 600

### "Host key verification failed"

- Update `DREAMHOST_KNOWN_HOSTS` with the current host key:
  ```bash
  ssh-keyscan -H your-dreamhost-server.dreamhost.com
  ```

### Files deployed but application shows errors

- Check DreamHost error logs: `~/logs/yourdomain.com/http/error.log`
- Verify virtual environment is activated and dependencies are installed
- Ensure `dispatch.fcgi` or `dispatch.cgi` has execute permissions (755)

### rsync errors

- Verify `DREAMHOST_PATH` exists and your user has write permissions
- Check that rsync is available on the DreamHost server

## Manual Deployment Alternative

If you prefer to deploy manually without GitHub Actions:

```bash
# From your local repository directory
rsync -avz --delete \
  --exclude='.git' \
  --exclude='venv' \
  --exclude='cache' \
  --exclude='__pycache__' \
  ./ yourusername@yourserver.dreamhost.com:/home/yourusername/path/to/simple-album/

# Then SSH in and set permissions
ssh yourusername@yourserver.dreamhost.com
cd /home/yourusername/path/to/simple-album
chmod 755 dispatch.fcgi dispatch.cgi
mkdir -p cache
chmod 755 cache
```

## Customization

### Deploy on Different Branches

Edit `.github/workflows/deploy-dreamhost.yml`:

```yaml
on:
  push:
    branches:
      - main
      - production  # Add more branches
```

### Deploy Only Specific Paths

Modify the `rsync` command to include only specific directories:

```yaml
rsync -avz --delete \
  --include='app.py' \
  --include='dispatch.*' \
  --include='.htaccess' \
  --exclude='*' \
  ./ "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/"
```

### Add Deployment Notifications

Add a step to notify via email, Slack, or Discord when deployment completes.
