# Ruby Cheat Sheet

## Gem Install

Installing a gem on macOS runs straight into the Apple-managed system Ruby: no write access, no clean place to put it. The pinned `--user-install` form sidesteps that, at the cost of a flag combination that looks contradictory.

```bash
# Install a specific pinned version of a gem for the invoking user only
sudo gem install <GEM_NAME> -v <GEM_VERSION> --user-install
```

**Uncertain — flag conflict left as-is:** `sudo` installs as root while `--user-install` targets the invoking user's home directory. This is a known macOS footgun where the gem can land somewhere neither the user nor root expects. It is kept here unmodified because it is field-tested and worked on the source system — not corrected.

## Gem Environment Setup

A `pod`/`gem`/`ruby` command not found after install, on a toolchain that includes CocoaPods, means the gem-installed executables were never put on `PATH`. `GEM_HOME` has to be set first since `RUBY_HOME` and `COCOAPODS_HOME` are both derived paths underneath it — then each `bin/` gets prepended, and the whole block needs to be persisted or it's gone the moment the shell closes.

```bash
# 1. Point GEM_HOME at a user-owned gem root, derive the versioned Ruby
#    and CocoaPods gem paths under it, then prepend each bin/ onto PATH
export GEM_HOME=$HOME/.gem
export RUBY_HOME=$GEM_HOME/ruby/2.6.0
export COCOAPODS_HOME=$GEM_HOME/ruby/2.6.0/gems/cocoapods-1.16.2
export PATH=$GEM_HOME/bin:$RUBY_HOME/bin:$COCOAPODS_HOME/bin:$PATH

# 2. Persist it — without this, the exports above are gone on next login/shell
vi <USER_HOME>/.bash_profile
```

## Key Patterns

| Symptom | Move |
|---|---|
| Gem install fails against Apple-managed system Ruby | `sudo gem install <GEM_NAME> -v <GEM_VERSION> --user-install` (flag combo is contradictory but field-tested) |
| `gem`/`ruby`/`pod` command not found after install | Export `GEM_HOME` → derive `RUBY_HOME` and `COCOAPODS_HOME` under it → prepend each `bin/` onto `PATH` |
| PATH export disappears in a new terminal/session | Add the same exports to `.bash_profile` so they persist |
