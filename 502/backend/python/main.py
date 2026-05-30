import sys
import json
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer import VideoAnalyzer


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <command> <args_json>", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "analyze":
        if len(sys.argv) < 3:
            print("Usage: python main.py analyze <video_path> [options_json]", file=sys.stderr)
            sys.exit(1)

        video_path = sys.argv[2]
        options = {}
        if len(sys.argv) >= 4:
            try:
                options = json.loads(sys.argv[3])
            except json.JSONDecodeError:
                print("Invalid options JSON", file=sys.stderr)
                sys.exit(1)

        if not os.path.exists(video_path):
            result = {"error": f"Video file not found: {video_path}", "success": False}
            print(json.dumps(result, ensure_ascii=False))
            sys.exit(1)

        analyzer = VideoAnalyzer(
            sensitivity=options.get("sensitivity", 1.0),
            sample_fps=options.get("sample_fps", 2)
        )

        result = analyzer.analyze(video_path, options)
        print(json.dumps(result, ensure_ascii=False))

    elif command == "compile":
        if len(sys.argv) < 5:
            print("Usage: python main.py compile <video_path> <highlights_json> <output_path> [options_json]", file=sys.stderr)
            sys.exit(1)

        video_path = sys.argv[2]
        highlights = json.loads(sys.argv[3])
        output_path = sys.argv[4]
        options = {}
        if len(sys.argv) >= 6:
            try:
                options = json.loads(sys.argv[5])
            except json.JSONDecodeError:
                pass

        analyzer = VideoAnalyzer()
        result = analyzer.generate_compilation(video_path, highlights, output_path, options)
        print(json.dumps(result, ensure_ascii=False))

    elif command == "info":
        if len(sys.argv) < 3:
            print("Usage: python main.py info <video_path>", file=sys.stderr)
            sys.exit(1)

        from analyzer.ffmpeg_processor import FFmpegProcessor
        video_path = sys.argv[2]
        info = FFmpegProcessor.get_video_info(video_path)
        if info:
            print(json.dumps(info, ensure_ascii=False))
        else:
            print(json.dumps({"error": "Cannot read video info"}, ensure_ascii=False))
            sys.exit(1)

    elif command == "export":
        if len(sys.argv) < 4:
            print("Usage: python main.py export <input_path> <output_path> [options_json]", file=sys.stderr)
            sys.exit(1)

        from analyzer.ffmpeg_processor import FFmpegProcessor
        input_path = sys.argv[2]
        output_path = sys.argv[3]
        options = {}
        if len(sys.argv) >= 5:
            try:
                options = json.loads(sys.argv[4])
            except json.JSONDecodeError:
                pass

        success = FFmpegProcessor.export_video(
            input_path, output_path,
            format_type=options.get("format", "mp4"),
            resolution=options.get("resolution", "original"),
            quality=options.get("quality", "balanced")
        )

        print(json.dumps({"success": success, "output_path": output_path}, ensure_ascii=False))

    elif command == "presets":
        from analyzer.ffmpeg_processor import FFmpegProcessor
        presets = FFmpegProcessor.get_quality_presets()
        print(json.dumps({"presets": presets}, ensure_ascii=False))

    elif command == "estimate_size":
        if len(sys.argv) < 4:
            print("Usage: python main.py estimate_size <duration_seconds> [options_json]", file=sys.stderr)
            sys.exit(1)

        from analyzer.ffmpeg_processor import FFmpegProcessor
        duration = float(sys.argv[2])
        options = {}
        if len(sys.argv) >= 4:
            try:
                options = json.loads(sys.argv[3])
            except json.JSONDecodeError:
                pass

        estimate = FFmpegProcessor.estimate_file_size(
            duration,
            quality=options.get("quality", "balanced"),
            resolution=options.get("resolution", "1080p")
        )
        print(json.dumps(estimate, ensure_ascii=False))

    elif command == "recommend_music":
        if len(sys.argv) < 5:
            print("Usage: python main.py recommend_music <video_path> <highlights_json> <scenes_json> [options_json]", file=sys.stderr)
            sys.exit(1)

        video_path = sys.argv[2]
        highlights = json.loads(sys.argv[3])
        scenes = json.loads(sys.argv[4])
        options = {}
        if len(sys.argv) >= 6:
            try:
                options = json.loads(sys.argv[5])
            except json.JSONDecodeError:
                pass

        analyzer = VideoAnalyzer()
        result = analyzer.recommend_music(video_path, highlights, scenes, options)
        print(json.dumps(result, ensure_ascii=False))

    elif command == "generate_subtitles":
        if len(sys.argv) < 3:
            print("Usage: python main.py generate_subtitles <video_path> [options_json]", file=sys.stderr)
            sys.exit(1)

        video_path = sys.argv[2]
        options = {}
        if len(sys.argv) >= 4:
            try:
                options = json.loads(sys.argv[3])
            except json.JSONDecodeError:
                pass

        analyzer = VideoAnalyzer()
        result = analyzer.generate_subtitles(video_path, options)
        print(json.dumps(result, ensure_ascii=False))

    elif command == "export_subtitles":
        if len(sys.argv) < 4:
            print("Usage: python main.py export_subtitles <video_path> <output_path> [options_json]", file=sys.stderr)
            sys.exit(1)

        video_path = sys.argv[2]
        output_path = sys.argv[3]
        options = {}
        if len(sys.argv) >= 5:
            try:
                options = json.loads(sys.argv[4])
            except json.JSONDecodeError:
                pass

        analyzer = VideoAnalyzer()
        result = analyzer.export_subtitles(video_path, output_path, options)
        print(json.dumps(result, ensure_ascii=False))

    elif command == "get_templates":
        options = {}
        if len(sys.argv) >= 3:
            try:
                options = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                pass

        analyzer = VideoAnalyzer()
        result = analyzer.get_templates(options)
        print(json.dumps(result, ensure_ascii=False))

    elif command == "apply_template":
        if len(sys.argv) < 5:
            print("Usage: python main.py apply_template <template_id> <highlights_json> <scenes_json> [options_json]", file=sys.stderr)
            sys.exit(1)

        template_id = sys.argv[2]
        highlights = json.loads(sys.argv[3])
        scenes = json.loads(sys.argv[4])
        options = {}
        if len(sys.argv) >= 6:
            try:
                options = json.loads(sys.argv[5])
            except json.JSONDecodeError:
                pass

        analyzer = VideoAnalyzer()
        result = analyzer.apply_template(template_id, highlights, scenes, options)
        print(json.dumps(result, ensure_ascii=False))

    elif command == "get_music_library":
        analyzer = VideoAnalyzer()
        result = analyzer.get_music_library()
        print(json.dumps(result, ensure_ascii=False))

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
