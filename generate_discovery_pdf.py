import os
import subprocess
import sys


def generate_pdf():
    docs_dir = os.path.join(os.getcwd(), "docs")
    html_path = os.path.join(docs_dir, "sme_data_pipeline_discovery_guide.html")
    pdf_path = os.path.join(docs_dir, "sme_data_pipeline_discovery_guide.pdf")

    if not os.path.exists(html_path):
        print(f"[ERROR] {html_path} does not exist.")
        sys.exit(1)

    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    edge_bin = next((p for p in edge_paths if os.path.exists(p)), None)

    if not edge_bin:
        print("[ERROR] Microsoft Edge executable not found.")
        sys.exit(1)

    cmd = [
        edge_bin,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path,
    ]
    print("[RUN] Converting to PDF via Edge Headless...")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        size_kb = os.path.getsize(pdf_path) / 1024
        print(f"[SUCCESS] PDF successfully created: {pdf_path} ({size_kb:.1f} KB)")
    else:
        print(f"[ERROR] Failed to generate PDF: {result.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    generate_pdf()
