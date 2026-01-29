#!/usr/bin/env python3
"""
Create a completely static HTML version for PDF export

No JavaScript, all slides visible, optimized for printing.
"""
from pathlib import Path
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ BeautifulSoup4 未安装")
    print("请运行: pip install beautifulsoup4")
    exit(1)


def create_static_html():
    """Create a static HTML version with all slides visible"""

    project_root = Path(__file__).parent.parent
    html_file = project_root / "docs" / "presentation.html"
    static_file = project_root / "docs" / "presentation_static.html"

    # Read the original HTML
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse with BeautifulSoup
    soup = BeautifulSoup(content, 'html.parser')

    # Find all slide divs
    slides = soup.find_all('div', class_='slide')

    print(f"找到 {len(slides)} 张幻灯片")

    # Build static HTML
    static_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Dev Dashboard - 推广介绍</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: #0a0a0a;
            color: #e8eaed;
        }

        .slide {
            width: 100%;
            min-height: 100vh;
            display: block;
            page-break-after: always;
            page-break-inside: avoid;
            padding: 50px 60px;
            position: relative;
        }

        .slide:last-child {
            page-break-after: avoid;
        }

        /* Title Slide */
        .slide.title {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
        }

        .slide.title h1 {
            font-size: 3rem;
            margin-bottom: 20px;
            background: linear-gradient(90deg, #8ab4f8, #a78bfa, #fbbf24);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .slide.title .subtitle {
            font-size: 1.4rem;
            color: #a7adb3;
            margin-bottom: 40px;
        }

        .slide.title .tagline {
            font-size: 1.1rem;
            color: #8ab4f8;
            max-width: 800px;
            line-height: 1.8;
        }

        /* Content Styles */
        .slide h2 {
            font-size: 2rem;
            margin-bottom: 30px;
            color: #8ab4f8;
        }

        .slide h3 {
            font-size: 1.4rem;
            margin-bottom: 15px;
            color: #e8eaed;
        }

        .slide p, .slide li {
            font-size: 1rem;
            line-height: 1.7;
            color: #c8ccd1;
            margin-bottom: 15px;
        }

        .slide ul {
            margin-left: 40px;
        }

        .slide li {
            margin-bottom: 15px;
        }

        /* Feature Cards */
        .features-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 25px;
            margin-top: 30px;
        }

        .feature-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 25px;
        }

        .feature-card .icon {
            font-size: 2.5rem;
            margin-bottom: 15px;
        }

        .feature-card h4 {
            font-size: 1.2rem;
            margin-bottom: 10px;
            color: #e8eaed;
        }

        .feature-card p {
            font-size: 0.95rem;
            margin: 0;
        }

        /* Comparison */
        .comparison {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            margin-top: 30px;
        }

        .comparison-column {
            padding: 25px;
            border-radius: 16px;
        }

        .comparison-column.traditional {
            background: rgba(183, 28, 28, 0.1);
            border: 1px solid rgba(183, 28, 28, 0.3);
        }

        .comparison-column.agent {
            background: rgba(46, 125, 50, 0.1);
            border: 1px solid rgba(46, 125, 50, 0.3);
        }

        .comparison-column h3 {
            margin-bottom: 20px;
        }

        .comparison-column.traditional h3 {
            color: #ffc1c1;
        }

        .comparison-column.agent h3 {
            color: #b7f3b7;
        }

        /* Architecture */
        .architecture {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 30px 0;
            flex-wrap: wrap;
            gap: 15px;
        }

        .arch-flow {
            display: flex;
            justify-content: center;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }

        .arch-box {
            background: rgba(138, 180, 248, 0.1);
            border: 2px solid #8ab4f8;
            border-radius: 12px;
            padding: 15px 25px;
            font-size: 1rem;
        }

        .arch-arrow {
            font-size: 1.5rem;
            color: #8ab4f8;
        }

        /* ADSE Steps */
        .adse-steps {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 25px;
            margin-top: 30px;
        }

        .adse-step {
            background: rgba(167, 139, 250, 0.1);
            border: 1px solid rgba(167, 139, 250, 0.3);
            border-radius: 16px;
            padding: 25px;
            text-align: center;
        }

        .adse-step .step-number {
            display: inline-block;
            width: 50px;
            height: 50px;
            line-height: 50px;
            border-radius: 50%;
            background: #a78bfa;
            color: #0a0a0a;
            font-weight: bold;
            margin-bottom: 15px;
        }

        .adse-step h4 {
            font-size: 1.2rem;
            margin-bottom: 10px;
            color: #a78bfa;
        }

        .adse-step p {
            font-size: 0.9rem;
        }

        /* Use Cases */
        .use-cases {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 25px;
            margin-top: 30px;
        }

        .use-case {
            background: rgba(251, 191, 36, 0.1);
            border: 1px solid rgba(251, 191, 36, 0.3);
            border-radius: 16px;
            padding: 25px;
        }

        .use-case h4 {
            font-size: 1.2rem;
            margin-bottom: 10px;
            color: #fbbf24;
        }

        .use-case p {
            font-size: 0.95rem;
        }

        /* CTA Slide */
        .slide.cta {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
        }

        .slide.cta h1 {
            font-size: 2.5rem;
            margin-bottom: 20px;
        }

        .cta-links {
            display: flex;
            gap: 30px;
            justify-content: center;
            margin-top: 40px;
            flex-wrap: wrap;
        }

        .cta-links a {
            color: #8ab4f8;
            text-decoration: none;
            font-size: 1.1rem;
        }

        /* Print optimization */
        @media print {
            @page {
                size: A4 landscape;
                margin: 0.5cm;
            }

            * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }

            body {
                background: #0a0a0a !important;
                -webkit-print-color-adjust: exact !important;
            }

            .slide {
                page-break-after: always !important;
                page-break-inside: avoid !important;
            }

            .slide:last-child {
                page-break-after: avoid !important;
            }
        }
    </style>
</head>
<body>
"""

    # Add each slide
    for i, slide in enumerate(slides, 1):
        # Get the slide classes
        classes = slide.get('class', [])
        if 'title' in classes:
            slide_class = 'slide title'
        elif 'cta' in classes:
            slide_class = 'slide cta'
        else:
            slide_class = 'slide'

        # Convert the slide back to HTML
        slide_html = str(slide)

        # Remove the outer div wrapper since we'll add our own
        # Extract just the inner content
        inner_content = slide.decode_contents()

        static_html += f'<!-- Slide {i} -->\n<div class="{slide_class}">\n{inner_content}\n</div>\n\n'

    static_html += '</body>\n</html>'

    # Write the static file
    with open(static_file, 'w', encoding='utf-8') as f:
        f.write(static_html)

    print(f"✅ 静态 HTML 已创建: {static_file}")
    print(f"✅ 共提取 {len(slides)} 张幻灯片")
    print()
    print("📄 导出 PDF 步骤：")
    print("  1. 在浏览器中打开文件")
    print(f"     open {static_file}")
    print("  2. 按 Cmd+P (Mac) 或 Ctrl+P (Windows)")
    print("  3. 纸张: A4 横向")
    print("  4. 边距: 默认")
    print("  5. ✅ 勾选 '打印背景图形'")
    print("  6. 保存为 PDF")
    print()
    print("💡 说明:")
    print("  - 纯静态 HTML，无 JavaScript")
    print("  - 所有幻灯片一次性显示")
    print("  - 适合导出 PDF")


if __name__ == "__main__":
    create_static_html()
