#!/usr/bin/env python3
"""
ad-hoc: verify paper build — reusable for any paper-mendel-mamba style project.
Usage: python verify.py [--keep] [--src src/paper.tex]
"""
import subprocess, os, sys, argparse

def build(tex_rel: str) -> str:
    tex_rel = os.path.abspath(tex_rel)  # make absolute
    proj = os.path.dirname(os.path.dirname(tex_rel))  # /path/to/project
    build_dir = os.path.join(proj, "build")
    out_dir  = os.path.join(proj, "output")
    name     = os.path.splitext(os.path.basename(tex_rel))[0]
    pdf_out  = os.path.join(build_dir, f"{name}.pdf")

    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    def run(cmd, **kw):
        r = subprocess.run(cmd, cwd=proj, capture_output=True, text=True, timeout=180, errors="replace", **kw)
        errs = [l.strip() for l in r.stdout.split("\n") if l.startswith("! ") and "rerunfilecheck" not in l]
        if errs:
            for e in errs: print(f"  ERR: {e}")
            sys.exit(1)
        return r

    # Pass 1-2 xelatex → biber → xelatex × 2
    for _ in range(2):
        run(["xelatex", "-interaction=nonstopmode", "-output-directory", build_dir, tex_rel])
    biber = run(["biber", os.path.join(build_dir, name)], check=False)
    if biber.returncode != 0:
        for l in biber.stdout.split("\n"):
            if "WARN" in l: print(f"  BIB WARN: {l.strip()}")
    for _ in range(2):
        run(["xelatex", "-interaction=nonstopmode", "-output-directory", build_dir, tex_rel])

    assert os.path.exists(pdf_out), "PDF not produced"
    return pdf_out, name, out_dir

def verify(pdf_path: str, checks: list) -> int:
    txt = subprocess.run(["pdftotext", "-layout", pdf_path, "-"],
                         capture_output=True, text=True, timeout=30, errors="replace").stdout
    pages = txt.count("\x0c") + 1
    sz = os.path.getsize(pdf_path)
    content = txt.lower()
    ok = 0
    for label, kw in checks:
        if callable(kw):
            if kw(content): ok += 1
            else: print(f"  MISSING: {label}")
        elif kw in content:
            ok += 1
        else:
            print(f"  MISSING: {label}/{kw}")
    print(f"PASS: {pages}p {sz//1024}KB {ok}/{len(checks)} sections OK")
    return 0 if ok == len(checks) else 1

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="src/Ma_Mendel_Mamba_2026.tex")
    ap.add_argument("--keep", action="store_true", help="keep build dir")
    args = ap.parse_args()

    pdf, name, out = build(args.src)
    checks = [
        ("abstract", "mendel"),
        ("intro", "gregor mendel"),
        ("mendelian", "threshold function"),
        ("epigenetics", "dna methylation"),
        ("snn", "leaky integrate-and-fire"),
        ("ssm", "state-space model"),
        ("mamba", "selective ssm"),
        ("complexity", lambda c: "o(n" in c or "quadratic" in c),
        ("discussion", "limitations"),
        ("references", lambda c: "mcculloch" in c or "mendel1866" in c),
    ]
    rv = verify(pdf, checks)
    subprocess.run(["cp", pdf, os.path.join(out, f"{name}.pdf")])
    if not args.keep:
        import shutil; shutil.rmtree(os.path.join(os.path.dirname(os.path.dirname(args.src)), "build"))
    sys.exit(rv)
