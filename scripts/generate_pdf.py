#!/usr/bin/env python3
"""
Create a print-friendly version of the presentation for PDF export.

This version shows ALL slides for printing (not just the active one).
"""
from pathlib import Path


def create_printable_html():
    """Create a printable HTML version with all slides visible"""

    # Read the original HTML
    project_root = Path(__file__).parent.parent
    html_file = project_root / "docs" / "presentation.html"
    printable_file = project_root / "docs" / "presentation_printable.html"

    print(f"读取文件: {html_file}")

    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Key modifications for printing:
    # 1. Remove 'display: none' from .slide class
    # 2. Remove JavaScript that hides slides
    # 3. Add print-specific CSS

    # Replace the slide style to remove display: none
    content = content.replace(
        '.slide {\n            width: 100%;\n            height: 100%;\n            display: none;\n            position: absolute;',
        '.slide {\n            width: 100%;\n            height: 100%;\n            display: block;\n            page-break-after: always;\n            position: relative;'
    )

    # Remove 'active' class handling and show all slides
    content = content.replace('class="slide active"', 'class="slide"')
    content = content.replace('class="slide active cta"', 'class="slide cta"')

    # Remove the animation that might interfere with printing
    content = content.replace(
        'animation: fadeIn 0.5s ease-in-out;',
        ''
    )

    # Add comprehensive print CSS
    print_css = """
        <style media="print">
            @page {
                size: A4 landscape;
                margin: 0;
            }

            * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                color-adjust: exact !important;
            }

            body {
                background: #0a0a0a !important;
            }

            .slides-container {
                position: static !important;
            }

            .slide {
                display: block !important;
                position: relative !important;
                page-break-after: always !important;
                page-break-inside: avoid !important;
                width: 100% !important;
                height: 100vh !important;
                min-height: 100vh !important;
            }

            .slide:last-child {
                page-break-after: avoid !important;
            }

            /* Hide navigation and controls */
            .navigation,
            .slide-number,
            .progress,
            .fullscreen-hint {
                display: none !important;
            }

            /* Ensure all colors print correctly */
            .feature-card,
            .adse-step,
            .use-case,
            .comparison-column,
            .arch-box,
            .title h1,
            .title .subtitle,
            .title .tagline {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
        </style>

        <style>
            /* Screen-only instruction banner */
            .print-instruction {
                position: fixed;
                top: 10px;
                right: 10px;
                background: #fff;
                color: #000;
                padding: 15px;
                border-radius: 8px;
                font-size: 13px;
                z-index: 10000;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                max-width: 300px;
            }

            .print-instruction h4 {
                margin: 0 0 10px 0;
                color: #8ab4f8;
            }

            .print-instruction p {
                margin: 5px 0;
                font-size: 12px;
            }

            .print-instruction button {
                margin-top: 10px;
                padding: 5px 15px;
                background: #8ab4f8;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
            }

            @media print {
                .print-instruction {
                    display: none !important;
                }
            }
        </style>
    """

    # Insert print CSS before </head>
    content = content.replace('</head>', print_css + '</head>')

    # Add instruction banner
    instruction = """
    <div class="print-instruction">
        <h4>📄 导出 PDF 说明</h4>
        <p><strong>macOS:</strong> Cmd+P → "另存为 PDF"</p>
        <p><strong>Windows:</strong> Ctrl+P → "Microsoft Print to PDF"</p>
        <p><strong>重要:</strong> 勾选 "打印背景图形"</p>
        <p><strong>纸张:</strong> A4 横向</p>
        <button onclick="this.parentElement.remove()">关闭提示</button>
    </div>
    """

    # Insert instructions after <body>
    content = content.replace('<body>', '<body>' + instruction)

    # Write printable version
    with open(printable_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 打印友好版本已创建: {printable_file}")
    print()
    print("下一步操作：")
    print("  1. 在浏览器中打开文件:")
    print(f"     open {printable_file}")
    print("  2. 按 Cmd+P (Mac) 或 Ctrl+P (Windows)")
    print("  3. 重要: 确保勾选 '打印背景图形' 选项")
    print("  4. 选择 '另存为 PDF'")
    print("  5. 点击保存")
    print()
    print(f"文件包含 {content.count('class=\"slide\"')} 张幻灯片")


if __name__ == "__main__":
    create_printable_html()
