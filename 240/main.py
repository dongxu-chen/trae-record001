import argparse
import asyncio
import signal
import sys
from config import Config
from asr import Wav2Vec2ASR
from websocket_server import ASRWebSocketServer


def parse_args():
    parser = argparse.ArgumentParser(description='中文语音识别系统')
    parser.add_argument('--mode', type=str, default='server',
                       choices=['server', 'mic', 'file'],
                       help='运行模式: server(WebSocket服务), mic(麦克风实时识别), file(文件识别)')
    parser.add_argument('--device', type=str, default='cpu',
                       help='运行设备: cpu 或 cuda')
    parser.add_argument('--port', type=int, default=8765,
                       help='WebSocket端口')
    parser.add_argument('--hotwords', type=str, default='',
                       help='自定义热词，用逗号分隔')
    parser.add_argument('--model', type=str, 
                       default='jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn',
                       help='Wav2Vec2模型名称')
    parser.add_argument('--file', type=str, default='',
                       help='音频文件路径(用于file模式)')
    parser.add_argument('--no-noise-suppression', action='store_true',
                       help='禁用噪声抑制')
    parser.add_argument('--enable-wakeword', action='store_true',
                       help='启用关键词唤醒检测')
    parser.add_argument('--wakewords', type=str, default='开始录音,你好,唤醒',
                       help='唤醒词列表，用逗号分隔')
    parser.add_argument('--enable-diarization', action='store_true',
                       help='启用说话人分离')
    parser.add_argument('--n-speakers', type=int, default=2,
                       help='说话人数量(默认: 2)')
    return parser.parse_args()


def run_server(args):
    config = Config.load_from_env()
    config.asr.device = args.device
    config.asr.model_name = args.model
    config.websocket.port = args.port
    
    if args.hotwords:
        config.hotword.hotwords = [w.strip() for w in args.hotwords.split(',') if w.strip()]
    
    config.noise_suppression.enable = not args.no_noise_suppression
    
    config.wake_word.enable = args.enable_wakeword
    if args.enable_wakeword and args.wakewords:
        config.wake_word.wake_words = [w.strip() for w in args.wakewords.split(',') if w.strip()]
    
    config.speaker_diarization.enable = args.enable_diarization
    config.speaker_diarization.n_speakers = args.n_speakers
    
    print("初始化ASR模型...")
    asr_model = Wav2Vec2ASR(config.asr, config.hotword)
    
    print(f"配置信息:")
    print(f"  - 噪声抑制: {'启用' if config.noise_suppression.enable else '禁用'}")
    print(f"  - 关键词唤醒: {'启用' if config.wake_word.enable else '禁用'}")
    if config.wake_word.enable:
        print(f"    - 唤醒词: {config.wake_word.wake_words}")
    print(f"  - 说话人分离: {'启用' if config.speaker_diarization.enable else '禁用'}")
    if config.speaker_diarization.enable:
        print(f"    - 说话人数量: {config.speaker_diarization.n_speakers}")
    
    print("启动WebSocket服务...")
    server = ASRWebSocketServer(
        config.websocket, config.vad, asr_model,
        config.noise_suppression, config.wake_word, config.speaker_diarization
    )
    
    def signal_handler(signum, frame):
        print("\n正在关闭服务...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n服务已关闭")


def run_mic(args):
    from audio_capture import RealtimeASRCapture, AudioCapture
    
    config = Config.load_from_env()
    config.asr.device = args.device
    config.asr.model_name = args.model
    
    if args.hotwords:
        config.hotword.hotwords = [w.strip() for w in args.hotwords.split(',') if w.strip()]
    
    config.noise_suppression.enable = not args.no_noise_suppression
    config.wake_word.enable = args.enable_wakeword
    if args.enable_wakeword and args.wakewords:
        config.wake_word.wake_words = [w.strip() for w in args.wakewords.split(',') if w.strip()]
    
    config.speaker_diarization.enable = args.enable_diarization
    config.speaker_diarization.n_speakers = args.n_speakers
    
    print("初始化ASR模型...")
    asr_model = Wav2Vec2ASR(config.asr, config.hotword)
    
    temp_audio = AudioCapture(config.audio, config.vad)
    devices = temp_audio.list_devices()
    print("\n可用音频设备:")
    for dev in devices:
        print(f"  [{dev['index']}] {dev['name']} (采样率: {dev['sample_rate']})")
    temp_audio.close()
    
    print(f"\n配置信息:")
    print(f"  - 噪声抑制: {'启用' if config.noise_suppression.enable else '禁用'}")
    print(f"  - 关键词唤醒: {'启用' if config.wake_word.enable else '禁用'}")
    if config.wake_word.enable:
        print(f"    - 唤醒词: {config.wake_word.wake_words}")
    print(f"  - 说话人分离: {'启用' if config.speaker_diarization.enable else '禁用'}")
    if config.speaker_diarization.enable:
        print(f"    - 说话人数量: {config.speaker_diarization.n_speakers}")
    
    print("\n初始化实时识别...")
    capture = RealtimeASRCapture(
        config.audio, config.vad, asr_model,
        config.noise_suppression, config.wake_word, config.speaker_diarization
    )
    
    print("开始监听，请说话... (按 Ctrl+C 停止)")
    if config.wake_word.enable and not config.wake_word.auto_start:
        print("* 系统处于休眠状态，请说出唤醒词启动识别")
    capture.start()
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止识别...")
        
        if args.enable_diarization:
            transcripts = capture.get_speaker_transcripts()
            if transcripts:
                print("\n各说话人转录结果:")
                for speaker_id, text in transcripts.items():
                    speaker_name = capture.audio_capture.speaker_diarizer.get_speaker_name(speaker_id)
                    print(f"  {speaker_name}: {text}")
        
        capture.close()


def run_file(args):
    import soundfile as sf
    from noise_suppression import NoiseSuppressor
    
    config = Config.load_from_env()
    config.asr.device = args.device
    config.asr.model_name = args.model
    
    if args.hotwords:
        config.hotword.hotwords = [w.strip() for w in args.hotwords.split(',') if w.strip()]
    
    config.noise_suppression.enable = not args.noise_suppression
    
    if not args.file:
        print("请指定音频文件路径: --file <path>")
        return
    
    print("初始化ASR模型...")
    asr_model = Wav2Vec2ASR(config.asr, config.hotword)
    
    print(f"读取音频文件: {args.file}")
    audio, sr = sf.read(args.file)
    
    if sr != config.asr.sample_rate:
        import scipy.signal
        number_of_samples = round(len(audio) * float(config.asr.sample_rate) / sr)
        audio = scipy.signal.resample(audio, number_of_samples)
        sr = config.asr.sample_rate
    
    if config.noise_suppression.enable:
        print("应用噪声抑制...")
        suppressor = NoiseSuppressor(sample_rate=sr)
        audio = suppressor.rnnoise.process_audio(audio)
    
    print("开始识别...")
    result = asr_model.transcribe(audio)
    
    print(f"\n识别结果: {result['text']}")
    print(f"置信度: {result['confidence']:.2%}")
    print(f"音频时长: {result['duration']:.2f}秒")
    
    matched_hotwords = result.get('matched_hotwords', [])
    if matched_hotwords:
        print(f"匹配热词: {matched_hotwords}")


def main():
    args = parse_args()
    
    if args.mode == 'server':
        run_server(args)
    elif args.mode == 'mic':
        run_mic(args)
    elif args.mode == 'file':
        run_file(args)


if __name__ == '__main__':
    main()
