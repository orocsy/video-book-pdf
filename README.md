# Video Book PDF

离线把电子书翻页录屏还原为有序页图，再生成真正逐像素无损的归档 PDF 或体积更小的有损阅读 PDF。原始视频保持不变，不需要 API Key、云端上传或 GPU。

Skill 在 [skills/video-book-pdf/SKILL.md](skills/video-book-pdf/SKILL.md)。核心步骤：记录原视频时间戳 → 提出清晰页候选 → 检查漏页/重复页 → 精确抽取原始尺寸 PNG → 比较 PDF 编码 → 渲染和文字复核。自动候选不等于全书已验收。

要求：Python 3.12+、ffmpeg/ffprobe、带 OpenJPEG 的 Pillow。建议在独立虚拟环境安装 `requirements.txt`，执行 `python -m unittest discover -s tests -v`。安装 Skill 时，把完整 `skills/video-book-pdf` 目录复制到 agent 的技能目录；不要只复制 SKILL.md。

第一版支持 PNG 证据、原始 PTS 抽帧、页面顺序检查、可逆 JPEG 2000、经过像素/边缘误差比较的紧凑 JPX，以及兼容性更广的 JPEG 基线。所有输出拒绝覆盖已有文件。PDF 不包含 OCR 文字层。

在一份私人录屏的实测中，95 页阅读版从 41.66 MB 降到 30.25 MB，像素尺寸保持 1668×2388。这两份都是有损阅读版；无损模式另行保存，并逐页比较 RGB 像素。结果不能保证适用于其他书。完整方法与局限见 [compression.md](skills/video-book-pdf/references/compression.md)。

仓库只发布通用代码和合成测试，不含书页、视频、凭据或实际知识库。

MIT License. Dependencies keep their own licenses; install ffmpeg separately and follow its build/license terms.
