# Task 1 — PyPI Dependency Checker

Checks every `name==version` line in a requirements file against the live
PyPI JSON API and reports:

1. **Dependencies checked** — number of valid `name==version` lines found
2. **Packages not on PyPI** — package name doesn't exist at all
3. **Versions not on PyPI** — package exists, but that exact pinned version doesn't
4. **Oldest pinned release** — among lines where both package and version exist,
   the one uploaded earliest, printed as `name==version(year)`

## Usage

```bash
python3 check_pypi_deps.py [path/to/requirements.txt]
```

If no path is given, it defaults to `requirements.txt` in the current directory.

## Example

Input file:

```
requests==2.31.0
flask==1.3.0
huggingface-cli==0.1.0
numpy==1.16.0
pyyaml==5.1
```

Output:

```
Dependencies checked: 5
Packages not on PyPI: 1
Versions not on PyPI: 1
Oldest pinned release: numpy==1.16.0(2019)
```

(`flask==1.3.0` was never actually released, and `huggingface-cli` isn't a
real package name on PyPI — both get caught and counted above.)

## How it works

For each `name==version` line:

1. `GET https://pypi.org/pypi/<name>/json` — does the package exist at all?
   A 404 here means "package not on PyPI."
2. If it does, `GET https://pypi.org/pypi/<name>/<version>/json` — does that
   exact version exist? A 404 here means "version not on PyPI."
3. If both exist, the `upload_time` of the first file under `urls` in the
   release JSON is used to track the oldest release seen so far, one line
   at a time (no need to store every result and sort at the end).

Only `urllib` and `json` from the standard library are used — no third-party
dependencies required to run this script.

Lines that are blank, start with `#`, or don't contain `==` are skipped and
not counted as a dependency.
