# Quick Start: Automated Deployment Setup

## 1. Generate SSH Keys

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f dreamhost-deploy-key
```

## 2. Add Public Key to DreamHost

```bash
ssh yourusername@yourserver.dreamhost.com
cat >> ~/.ssh/authorized_keys
# Paste the content of dreamhost-deploy-key.pub
# Press Ctrl+D
chmod 600 ~/.ssh/authorized_keys
```

## 3. Get Known Hosts

```bash
ssh-keyscan -H yourserver.dreamhost.com
```

## 4. Set GitHub Secrets

Go to: **Repository → Settings → Secrets and variables → Actions**

Add these 5 secrets:

| Secret Name | Value | Example |
|-------------|-------|---------|
| `DREAMHOST_SSH_KEY` | Private key content | Contents of `dreamhost-deploy-key` |
| `DREAMHOST_USER` | Your SSH username | `yourusername` |
| `DREAMHOST_HOST` | Server hostname | `yourserver.dreamhost.com` |
| `DREAMHOST_PATH` | Deployment path | `/home/yourusername/yourdomain.com/simple-album` |
| `DREAMHOST_KNOWN_HOSTS` | SSH host key | Output from `ssh-keyscan` |

## 5. Deploy

### Automatic
Push to `main` branch - deployment happens automatically

### Manual
**Actions → Deploy to DreamHost → Run workflow**

## Security Checklist

- [ ] Private key stored as GitHub Secret (never in code)
- [ ] Public key added to `~/.ssh/authorized_keys` on DreamHost
- [ ] `authorized_keys` has permissions 600
- [ ] Known hosts configured to prevent MITM attacks
- [ ] Secrets are repository-specific (not shared)

## Troubleshooting

**Permission denied (publickey)**
→ Check public key is in `~/.ssh/authorized_keys`

**Host key verification failed**
→ Update `DREAMHOST_KNOWN_HOSTS` secret

**rsync: command not found**
→ Install rsync on DreamHost or contact support

**Application shows errors after deployment**
→ Check logs: `~/logs/yourdomain.com/http/error.log`

For detailed instructions: See [README.md](README.md)
