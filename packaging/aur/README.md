# AUR package

`releaseguard` installs the unmodified release archive from
<https://github.com/Shadoww23/releaseguard/releases/tag/v0.1.0-alpha>:
the CLI at `/usr/bin/releaseguard`, examples in
`/usr/share/releaseguard/examples`, and docs/licenses under `/usr/share`.

Build and verify (from a clean Arch container or an Arch host):

```sh
makepkg -f
namcap releaseguard-*.pkg.tar.zst
sudo pacman -U releaseguard-*.pkg.tar.zst
releaseguard --version
```

`makepkg` runs the unit tests in `check()`.

## Verified build (2026-10-21)

Built and installed in a clean `archlinux:latest` container:

```sh
makepkg -f --nodeps --noconfirm
namcap releaseguard-0.1.0_alpha-1-any.pkg.tar.zst
sudo pacman -U releaseguard-0.1.0_alpha-1-any.pkg.tar.zst
```

- `check()` unit tests passed.
- `namcap` reported no errors. The remaining warnings are false positives for
  the Windows-only `winreg` import and `python3`.
- Smoke tests passed: `releaseguard --version` and `releaseguard --help`.

## Publishing to the AUR

The package name `releaseguard` is unclaimed. Publishing needs an AUR account
with your SSH public key added at <https://aur.archlinux.org/account/>.

```sh
makepkg --printsrcinfo > .SRCINFO
git clone ssh://aur@aur.archlinux.org/releaseguard.git
cp PKGBUILD .SRCINFO releaseguard/
cd releaseguard && git add PKGBUILD .SRCINFO && git commit -m "Initial import"
git push
```
