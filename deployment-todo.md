# Deployment TODO

## WINGET_GITHUB_TOKEN

The winget submission workflow requires a GitHub Personal Access Token (PAT) stored
as a repository secret. Here is how to create and register it.

### Step 1 — Open GitHub token settings

Navigate to:
**github.com → avatar (top right) → Settings → Developer settings → Personal access tokens → Classic tokens**

### Step 2 — Generate a new token

Click **"Generate new token (classic)"**.

| Field | Value |
|---|---|
| Note | `winget-submit-sshman` |
| Expiration | 1 year (or your preference) |
| Scopes | `public_repo` |

`public_repo` is the only scope needed — it covers forking, pushing, and opening
PRs against public repositories, which is everything `wingetcreate` requires.

### Step 3 — Copy the token

GitHub shows the token **once**. Copy it before navigating away.

### Step 4 — Add it to the repository as a secret

1. Go to the `sshman` repository on GitHub
2. **Settings → Secrets and variables → Actions**
3. Click **"New repository secret"**
4. Name: `WINGET_GITHUB_TOKEN`
5. Value: paste the token
6. Click **"Add secret"**

### Step 5 — First-run behaviour

On the first run, `wingetcreate` will automatically fork `microsoft/winget-pkgs`
into your account if a fork does not already exist. No manual action is required.

---

## Winget submission review process

`wingetcreate submit` opens a pull request against `microsoft/winget-pkgs`.

- **First submission** of `Dejan.sshman` requires passing automated validation
  and a manual review by the Microsoft winget team. Expect a few days to a week.
- **Subsequent version updates** are faster — the package is already known and
  only the automated checks need to pass.

Track the status of your PR at:
`https://github.com/microsoft/winget-pkgs/pulls` — search for `Dejan.sshman`.

---

## Phase 2 — Homebrew tap

Requires creating a separate public GitHub repository named `homebrew-sshman`.

- [ ] Create repo `dejan/homebrew-sshman` with a `Formula/` subdirectory
- [ ] Add `Formula/sshman.rb` — a `virtualenv_install_with_resources` formula
      with all transitive PyPI dependencies listed as `resource` blocks
      (use `homebrew-pypi-poet` or `brew update-python-resources` to generate them)
- [ ] Add a `HOMEBREW_TAP_GITHUB_TOKEN` secret to this repo (a PAT with `public_repo`
      scope on the `dejan/homebrew-sshman` repo, so the update workflow can push)
- [ ] Add `.github/workflows/update-homebrew.yml` to this repo — triggers after
      "Publish to PyPI" and auto-updates the formula for each new version

User install command: `brew install dejan/sshman/sshman`

---

## Phase 2 — AUR (Arch Linux)

Requires an AUR account and a registered SSH key.

- [ ] Create an account at `https://aur.archlinux.org` if you do not have one
- [ ] Generate a dedicated SSH key pair for CI use:
      `ssh-keygen -t ed25519 -C "sshman-aur-ci" -f ~/.ssh/aur_sshman`
- [ ] Register the **public key** in your AUR account:
      `https://aur.archlinux.org/account/<username>` → SSH Public Key
- [ ] Add the **private key** as a repository secret named `AUR_SSH_PRIVATE_KEY`
- [ ] Create the AUR package repo by pushing to `ssh://aur@aur.archlinux.org/sshman.git`
      with an initial `PKGBUILD` and `.SRCINFO`
- [ ] Optionally mirror it on GitHub as `dejan/aur-sshman` for visibility
- [ ] Add `.github/workflows/update-aur.yml` to this repo — triggers after
      "Publish to PyPI", updates `pkgver` and checksums, regenerates `.SRCINFO`,
      and pushes to the AUR

User install command: `yay -S sshman`
