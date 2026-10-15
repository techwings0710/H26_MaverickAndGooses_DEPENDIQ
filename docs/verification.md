# Controlled migration verification

The API accepts a scanned dependency name and exact PEP 440 version. It copies approved, regular, non-hidden files to baseline/migration directories, excludes key/certificate files and all symlinks, and edits only PEP 508 requirement literals for the selected package in the migration copy. Direct URL requirements are not rewritten. The UI discloses changed files and remaining conflicts. No AI-produced command or source patch is executed.

AST syntax and manifest comparisons always run without importing the target. These are OBSERVED checks, never passed project tests. Missing trust, execution opt-in, Docker, image, or executable scenario returns NOT RUN.

## Prepare offline execution

1. Inspect the target repository, its test code, manifests, includes, and test hooks. Containers reduce risk but are not a guarantee against hostile code. Run only inspected/trusted repositories on a disposable host if needed.
2. Install/start Docker Desktop from its official vendor. This build environment did not expose a working Docker CLI/daemon, so actual container execution is unverified.
3. Populate `wheelhouse/` with reviewed binary wheels for the **container platform and Python 3.12**, including pytest and transitive requirements for both scenarios. Do not assume macOS/Python 3.13 wheels work in Linux/Python 3.12.
4. Build the image manually. The backend never downloads images or dependencies.

Example for a reviewed requirements file whose wheels exist on your container platform:

```bash
mkdir -p wheelhouse
# This preparation step has network access; it is outside API verification.
# Use a disposable Docker container to download Linux wheels for its Python.
docker run --rm --mount "type=bind,src=$PWD/wheelhouse,dst=/wheels" python:3.12-slim python -m pip download --only-binary=:all: --dest /wheels pytest
# Add the inspected target requirements and selected migration version via
# explicit pip download specs in this same container environment.
# LinkWatch's old Pydantic pin may lack a wheel for the chosen Python/platform;
# record that installation blocker rather than changing the baseline silently.
docker build -f docs/verification.Dockerfile -t dependiq-verifier:local .
export DEPENDIQ_ENABLE_EXECUTION=1
export DEPENDIQ_VERIFY_IMAGE=dependiq-verifier:local
```

Restart the backend. Acknowledge repository trust in the verification screen, enter an exact version, and compare. Each fresh container uses `--pull=never --network=none --read-only --cap-drop=ALL --security-opt=no-new-privileges --user=65534:65534 --pids-limit=128 --cpus=1 --memory=1g`, read-only source mount, and temporary scratch. `pip --no-index --only-binary=:all: --find-links=/wheels --target=/tmp/deps` prepares dependencies; tests use `python -m pytest -q` with third-party plugin autoload disabled. Internal fixed install/test commands are printed in captured output; the outer container command, Python version, duration and exit code are recorded. Timeout cleanup force-removes only the specifically generated disposable container.

Counts are emitted by a fixed pytest reporting plugin. Collection/import failures can produce incomplete runs; installation failures leave counts null. Output is capped at 16 KB, so unusually verbose suites can lose the terminal summary and remain incomplete. Test completion never follows merely from a zero Docker exit code. A successful unchanged test suite cannot prove complete migration compatibility.

Only the latest explicit scenario per scan is stored in the prototype. Static comparison reads direct runtime TOML dependencies and requirements files; optional groups/includes may need manual review. No automatic source-code refactor is supported. The original checkout fingerprint is checked before copying; rescan if it changes.
