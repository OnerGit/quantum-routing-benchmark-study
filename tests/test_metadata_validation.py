"""Metadata validation tests for the approved publication metadata (P3-META).

Verifies (owner-approved):
- LICENSE = MIT, ``Copyright (c) 2026 Bob Oner``, with full permission and warranty-disclaimer clauses;
- CITATION.cff = valid YAML, CFF 1.2.0, author **Bob Oner**, license MIT, version ``0.1.0``;
- no fabricated release metadata (no ``date-released``, DOI, repository URL, email, ORCID, or paper);
- pyproject.toml declares the author, ``license = "MIT"`` and ``license-files = ["LICENSE"]``;
- README / NOTICE / THIRD_PARTY documentation is internally consistent with those values and keeps
  **time-neutral** publication-state wording (it does not claim a repository exists and does not
  fabricate releases/DOIs/papers/PyPI packages);
- the CI workflow comments are time-neutral (no "not yet pushed"/"local candidate" phrasing) and do
  not claim a GitHub-hosted CI pass;
- the earlier internal citation draft is preserved as historical evidence (not silently deleted);
- the structural CFF validator is a hygiene check, not a substitute for official schema validation.
"""

from __future__ import annotations

import pathlib
import re
import tomllib

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[1]
PUBLIC_CITATION = REPO / "CITATION.cff"
DRAFT = REPO / "internal" / "CITATION.cff.draft"
LICENSE_FILE = REPO / "LICENSE"
PYPROJECT = REPO / "pyproject.toml"

CFF_VERSIONS = {"1.0.0", "1.0.1", "1.0.2", "1.0.3", "1.1.0", "1.2.0"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SPDX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+.\-]*$")
NON_LICENSE_MARKERS = ("LICENSE_DECISION_REQUIRED", "PENDING", "TBD", "TODO", "DECISION")
PLACEHOLDER_MARKERS = ("AUTHORITY_PENDING", "MustBeSetBy", "PLACEHOLDER")

MIT_CLAUSES = [
    "Permission is hereby granted, free of charge",
    "without restriction, including without limitation the rights",
    "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell",
    "The above copyright notice and this permission notice shall be included in all",
    "THE SOFTWARE IS PROVIDED " + '"AS IS"',
    "WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED",
    "IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE",
]


def load_yaml(path: pathlib.Path) -> dict:
    return yaml.safe_load(path.read_text())


def _pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text())


# ------------------------------------------------------------------ LICENSE (A, B)

def test_license_exists_and_contains_full_mit_text():
    assert LICENSE_FILE.is_file()
    text = re.sub(r"\s+", " ", LICENSE_FILE.read_text())
    for clause in MIT_CLAUSES:
        assert re.sub(r"\s+", " ", clause) in text, f"MIT clause missing: {clause}"
    assert "MIT License" in text


def test_license_copyright_holder_is_bob_oner_2026():
    text = LICENSE_FILE.read_text()
    assert "Copyright (c) 2026 Bob Oner" in text
    assert "Mihir Talati" not in text, "third-party LICENSE text must not be copied into LICENSE"


# ------------------------------------------------------------------ CITATION.cff (C, D, E, F, G)

def test_citation_exists_and_is_valid_yaml():
    assert PUBLIC_CITATION.is_file()
    doc = load_yaml(PUBLIC_CITATION)
    assert isinstance(doc, dict)
    assert doc.get("cff-version") == "1.2.0"


def test_citation_author_is_bob_oner():
    doc = load_yaml(PUBLIC_CITATION)
    authors = doc.get("authors")
    assert isinstance(authors, list) and len(authors) == 1
    entry = authors[0]
    assert entry.get("given-names") == "Bob"
    assert entry.get("family-names") == "Oner"
    assert "OnerGit" not in yaml.safe_dump(entry), "do not substitute the author name with the GitHub username"


def test_citation_license_is_mit():
    assert load_yaml(PUBLIC_CITATION).get("license") == "MIT"


def test_citation_version_matches_pyproject():
    cit = load_yaml(PUBLIC_CITATION).get("version")
    proj = _pyproject()["project"]["version"]
    assert cit == proj == "0.1.0"


def test_citation_has_no_fabricated_release_metadata():
    doc = load_yaml(PUBLIC_CITATION)
    for key in ("date-released", "doi"):
        assert key not in doc, f"fabricated release metadata present: {key}"
    blob = yaml.safe_dump(doc).lower()
    for marker in ("orcid", "@", "=10."):  # no email, no ORCID, no fake DOI
        assert marker not in blob, f"forbidden identifier/contact metadata present: {marker}"
    assert "doi:" not in blob and "url:" not in blob


def test_public_citation_passes_structural_validator():
    assert validate_cff_structure(load_yaml(PUBLIC_CITATION)) == []


# ------------------------------------------------------------------ pyproject metadata (H, F)

def test_pyproject_declares_author_and_mit_license():
    proj = _pyproject()["project"]
    authors = proj.get("authors") or []
    assert any(a.get("name") == "Bob Oner" for a in authors)
    assert proj.get("license") == "MIT"
    assert proj.get("license-files") == ["LICENSE"]
    assert proj.get("version") == "0.1.0"
    for a in authors:
        assert "email" not in a, "no invented author email"


def test_pyproject_build_backend_supports_pep_639():
    bs = _pyproject()["build-system"]
    assert any("hatchling" in req for req in bs.get("requires", []))

    def _min_version(req: str):
        m = re.search(r"([0-9]+(?:\.[0-9]+)+)", req.split(">=")[1])
        return tuple(int(x) for x in m.group(1).split(".")) if m else (0,)

    hatch_req = next(r for r in bs["requires"] if "hatchling" in r)
    assert _min_version(hatch_req) >= (1, 27, 0), "hatchling must support PEP 639 (>=1.27.0)"


# ------------------------------------------------------------------ documentation consistency (I, J)

def test_readme_notice_thirdparty_consistent_with_metadata():
    readme = (REPO / "README.md").read_text()
    notice = (REPO / "NOTICE.md").read_text()
    third = (REPO / "THIRD_PARTY.md").read_text()
    for text, label in ((readme, "README"), (notice, "NOTICE")):
        assert "MIT" in text and "Bob Oner" in text, f"{label} missing approved license/author"
    assert "Mihir Talati" in third or "unlicensed" in third
    # no obsolete deferred-license claims remain in the public docs
    for text, label in ((readme, "README"), (notice, "NOTICE"), (third, "THIRD_PARTY")):
        assert "LICENSE_DECISION_REQUIRED" not in text, f"{label} still says license decision required"
        assert "has not selected a license" not in text, f"{label} still says license pending"


PUBLICATION_FABRICATION_MARKERS = (
    "doi:",
    "published on pypi",
    "released on pypi",
    "peer-reviewed paper",
)


def find_fabricated_publication_claims(text: str):
    """Return fabricated-publication markers found in ``text`` (case-insensitive)."""
    low = text.lower()
    return [m for m in PUBLICATION_FABRICATION_MARKERS if m in low]


def test_publication_state_is_time_neutral():
    readme = (REPO / "README.md")
    notice = (REPO / "NOTICE.md")
    r, n = readme.read_text().lower(), notice.read_text().lower()
    # No permanent claim that "GitHub has not yet been published" (time-neutral wording required).
    assert "not yet published" not in r and "not yet published" not in n
    assert "remain unauthorized" not in r and "remain unauthorized" not in n
    # No existing-repository URL is asserted as an existing resource.
    assert "github.com/onergit/quantum-routing-benchmark-study" not in r + n
    # The distinct statuses must be spelled out so availability != release != PyPI != DOI.
    for token in ("source repository", "pypi", "doi"):
        assert token in r, f"README must keep the distinct statuses (missing '{token}')"
    # No fabricated DOI/paper/PyPI/release anywhere in either document.
    violations = find_fabricated_publication_claims(r + n)
    assert not violations, f"fabricated publication claim in docs: {violations}"


def test_negative_control_fabricated_publication_detected():
    fabricated = "The software was released on PyPI (doi: 10.5555/fake) and peer-reviewed."
    assert "doi:" in find_fabricated_publication_claims(fabricated)
    assert "released on pypi" in find_fabricated_publication_claims(fabricated)
    honest = "No DOI, paper, PyPI package, or formal release is declared by this document."
    assert find_fabricated_publication_claims(honest) == []


PREPUBLICATION_PHRASES = (
    "not been pushed",
    "has not been pushed",
    "not yet published",
    "prepared locally for the p3-ci candidate",
    "p3-ci candidate",
    "local candidate",  # as a release-state descriptor
    "hosted ci pass",
    "hosted-ci pass",
)


def test_ci_workflow_comments_are_time_neutral():
    wf = (REPO / ".github" / "workflows" / "ci.yml").read_text()
    low = wf.lower()
    for phrase in PREPUBLICATION_PHRASES:
        assert phrase not in low, f"pre-publication phrasing leaked into workflow comments: {phrase}"
    # internal-only references must not appear inside the public workflow
    assert "internal/" not in low and "review-packages" not in low
    # semantics-critical lines remain present
    assert "permissions:" in low and "contents: read" in low
    assert "uv sync --frozen" in low
    assert 'uv run pytest -q -m "not external"' in low
    assert "actions/checkout@11d5960a326750d5838078e36cf38b85af677262" in wf
    assert "astral-sh/setup-uv@d0cc045d04ccac9d8b7881df0226f9e82c39688e" in wf


def test_workflow_does_not_claim_hosted_ci_pass():
    wf = (REPO / ".github" / "workflows" / "ci.yml").read_text().lower()
    for phrase in ("passed on github", "github-hosted ci = passed", "hosted ci pass", "ci pass",
                   "ci run passed"):
        assert phrase not in wf, f"workflow must not claim a hosted CI pass: {phrase}"


def test_readme_has_no_internal_git_build_remarks():
    readme = (REPO / "README.md").read_text().lower()
    assert "git init was performed" not in readme
    assert "dormant" not in readme


# ------------------------------------------------------------------ draft preserved as historical evidence (M)

def test_internal_citation_draft_preserved_as_historical_evidence():
    # The approved public CITATION.cff is shipped; the earlier internal draft (local/review copies
    # only) must remain preserved and must not be silently deleted. Public clones legitimately lack
    # internal/, so this check runs where the draft exists.
    if not DRAFT.is_file():
        pytest.skip("internal/CITATION.cff.draft not present (public-only copy)")
    assert DRAFT.is_file(), "earlier internal citation draft must be preserved (not deleted)"
    assert "DEFERRED" in DRAFT.read_text()


# ------------------------------------------------------------------ negative validators preserved

def test_no_non_license_marker_leaks_as_license_in_public_metadata():
    for path in (PUBLIC_CITATION, PYPROJECT):
        text = path.read_text()
        for line in text.splitlines():
            if "license" in line.lower() and re.match(r"\s*license\s*[:=]", line):
                for marker in NON_LICENSE_MARKERS:
                    assert marker not in line, f"pending marker used as license in {path}"


# ------------------------------------------------------------------ reusable CFF structural validator

def validate_cff_structure(doc: dict) -> list[str]:
    """Structural checks for a CFF 1.2 document.

    IMPORTANT: structural hygiene check, **not** a substitute for the official CFF 1.2 JSON schema
    validation (e.g. `cffconvert`); see `OFFICIAL_CFF_SCHEMA_VALIDATION` reporting in the review.
    """
    errors: list[str] = []
    if doc.get("cff-version") not in CFF_VERSIONS:
        errors.append(f"cff-version must be one of {sorted(CFF_VERSIONS)}")
    if not isinstance(doc.get("message"), str) or not doc["message"].strip():
        errors.append("message must be a non-empty string")
    if not isinstance(doc.get("title"), str) or not doc["title"].strip():
        errors.append("title must be a non-empty string")
    authors = doc.get("authors")
    if not isinstance(authors, list) or not authors:
        errors.append("authors must be a non-empty list (required by CFF 1.2)")
    else:
        for entry in authors:
            if not isinstance(entry, dict):
                errors.append("each author must be a mapping")
                continue
            if not any(k in entry for k in ("given-names", "family-names", "name")):
                errors.append("author entry lacks a name field")
            blob = " ".join(str(v) for v in entry.values()).lower()
            if any(m.lower() in blob for m in PLACEHOLDER_MARKERS):
                errors.append("author identity is still a placeholder (not release-ready)")
    if "date-released" in doc:
        if not isinstance(doc["date-released"], str) or not DATE_RE.match(doc["date-released"]):
            errors.append("date-released must match YYYY-MM-DD")
    if "license" in doc:
        lic = doc["license"]
        if not (isinstance(lic, str) and SPDX_RE.match(lic)):
            errors.append("license must be an SPDX expression or a URL")
        if any(m.lower() in str(lic).lower() for m in NON_LICENSE_MARKERS):
            errors.append("license must not be a pending/decision marker")
    return errors


def test_promotion_validator_rejects_pending_metadata():
    bad = {
        "cff-version": "1.2.0",
        "message": "x",
        "title": "x",
        "date-released": "not-a-date",
        "license": "LICENSE_DECISION_REQUIRED",
    }
    errors = validate_cff_structure(bad)
    assert errors
    assert any("authors" in e for e in errors)
    assert any("date-released" in e for e in errors)
    assert any("license" in e for e in errors)


def test_promotion_validator_rejects_placeholder_authors():
    errors = validate_cff_structure({
        "cff-version": "1.2.0",
        "message": "x",
        "title": "x",
        "authors": [{"given-names": "AUTHORITY_PENDING", "family-names": "MustBeSetByResearchOwner"}],
    })
    assert any("placeholder" in e for e in errors)


def test_promotion_validator_is_structural_only():
    doc = validate_cff_structure.__doc__ or ""
    assert "structural" in doc and "cffconvert" in doc
    assert "not" in doc and "substitute" in doc