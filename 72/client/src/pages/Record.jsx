import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mic, MicOff, Save, Loader2, Play, Pause, RotateCcw, Edit3 } from 'lucide-react';
import axios from 'axios';
import Waveform from '../components/Waveform';

function Record() {
  const navigate = useNavigate();
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [audioLevel, setAudioLevel] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [savedNote, setSavedNote] = useState(null);
  const [error, setError] = useState('');

  const recognitionRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const streamRef = useRef(null);
  const audioRef = useRef(null);
  const animationRef = useRef(null);
  const recordedBlobRef = useRef(null);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, []);

  const analyzeAudio = (stream) => {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);

    audioContextRef.current = audioContext;
    analyserRef.current = analyser;

    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    const updateLevel = () => {
      analyser.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
      setAudioLevel(average / 255);
      animationRef.current = requestAnimationFrame(updateLevel);
    };

    updateLevel();
  };

  const startRecording = async () => {
    setError('');
    setTranscript('');
    setSavedNote(null);
    audioChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      analyzeAudio(stream);

      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'zh-CN';

        recognition.onresult = (event) => {
          let interimTranscript = '';
          let finalTranscript = '';

          for (let i = 0; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += transcript + ' ';
            } else {
              interimTranscript += transcript;
            }
          }

          setTranscript(finalTranscript + interimTranscript);
        };

        recognition.onerror = (event) => {
          console.error('Speech recognition error:', event.error);
        };

        recognition.onend = () => {
          if (isRecording && !isPaused && recognitionRef.current) {
            try {
              recognition.start();
            } catch (e) {
              console.log('Speech recognition restart error:', e);
            }
          }
        };

        recognition.start();
        recognitionRef.current = recognition;
      }

      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(1000);

      setIsRecording(true);
      setIsPaused(false);
    } catch (err) {
      setError('无法访问麦克风，请确保已授予权限。');
      console.error(err);
    }
  };

  const pauseRecording = () => {
    if (recognitionRef.current) {
      recognitionRef.current.abort();
    }
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.pause();
    }
    setIsPaused(true);
  };

  const resumeRecording = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition && streamRef.current) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'zh-CN';

      recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = 0; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript + ' ';
          } else {
            interimTranscript += transcript;
          }
        }

        setTranscript(prev => prev + finalTranscript + interimTranscript);
      };

      recognition.start();
      recognitionRef.current = recognition;
    }

    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.resume();
    }
    setIsPaused(false);
  };

  const stopRecording = async () => {
    setIsProcessing(true);

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        console.log('Recognition stop error:', e);
      }
      recognitionRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      const recorder = mediaRecorderRef.current;

      await new Promise(resolve => {
        recorder.onstop = () => {
          const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          recordedBlobRef.current = blob;
          audioRef.current = new Audio(URL.createObjectURL(blob));
          resolve();
        };

        recorder.stop();
      });

      mediaRecorderRef.current = null;
    } else {
      if (audioChunksRef.current.length > 0) {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        recordedBlobRef.current = blob;
        audioRef.current = new Audio(URL.createObjectURL(blob));
      }
    }

    setIsRecording(false);
    setIsPaused(false);
    setAudioLevel(0);
    setIsProcessing(false);
  };

  const resetRecording = () => {
    setTranscript('');
    setSavedNote(null);
    setIsPlaying(false);
    recordedBlobRef.current = null;
    audioRef.current = null;
  };

  const playPreview = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play();
      setIsPlaying(true);
      audioRef.current.onended = () => {
        setIsPlaying(false);
      };
    }
  };

  const saveNote = async () => {
    if (!transcript.trim() && !recordedBlobRef.current) {
      setError('没有内容可保存。');
      return;
    }

    setIsProcessing(true);

    try {
      const formData = new FormData();
      formData.append('transcript', transcript);

      if (recordedBlobRef.current) {
        formData.append('audio', recordedBlobRef.current, 'recording.webm');
      }

      const response = await axios.post('/api/notes', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setSavedNote(response.data);
    } catch (err) {
      setError('保存笔记失败。' + (err.response?.data?.error || err.message));
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  const goToEdit = () => {
    if (savedNote) {
      navigate(`/edit/${savedNote._id}`);
    }
  };

  const formatTime = (ms) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '40px 20px',
    }}>
      <div style={{
        maxWidth: '800px',
        width: '100%',
        background: 'rgba(255, 255, 255, 0.95)',
        borderRadius: '20px',
        padding: '40px',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
      }}>
        <h1 style={{
          textAlign: 'center',
          fontSize: '32px',
          fontWeight: 700,
          marginBottom: '30px',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
        }}>
          语音笔记
        </h1>

        {error && (
          <div style={{
            background: '#fee2e2',
            color: '#991b1b',
            padding: '12px 16px',
            borderRadius: '8px',
            marginBottom: '20px',
            textAlign: 'center',
          }}>
            {error}
          </div>
        )}

        <div style={{
          background: '#f8fafc',
          borderRadius: '12px',
          padding: '24px',
          marginBottom: '24px',
        }}>
          <Waveform isRecording={isRecording && !isPaused} audioLevel={audioLevel} />
        </div>

        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '16px',
          marginBottom: '24px',
        }}>
          {!isRecording ? (
            <button
              onClick={startRecording}
              disabled={isProcessing}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '14px 32px',
                fontSize: '16px',
                fontWeight: 600,
                color: 'white',
                background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                border: 'none',
                borderRadius: '12px',
                cursor: 'pointer',
                transition: 'transform 0.2s, box-shadow 0.2s',
                boxShadow: '0 4px 14px rgba(239, 68, 68, 0.4)',
              }}
              onMouseOver={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
              onMouseOut={(e) => e.currentTarget.style.transform = 'scale(1)'}
            >
              <Mic size={20} />
              {isProcessing ? '处理中...' : '开始录音'}
            </button>
          ) : (
            <>
              <button
                onClick={isPaused ? resumeRecording : pauseRecording}
                disabled={isProcessing}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '14px 28px',
                  fontSize: '16px',
                  fontWeight: 600,
                  color: '#374151',
                  background: '#e5e7eb',
                  border: 'none',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  transition: 'transform 0.2s',
                }}
              >
                {isPaused ? <Play size={20} /> : <Pause size={20} />}
                {isPaused ? '继续' : '暂停'}
              </button>

              <button
                onClick={stopRecording}
                disabled={isProcessing}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '14px 28px',
                  fontSize: '16px',
                  fontWeight: 600,
                  color: 'white',
                  background: '#1f2937',
                  border: 'none',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  transition: 'transform 0.2s',
                }}
              >
                <MicOff size={20} />
                停止
              </button>
            </>
          )}

          {recordedBlobRef.current && !isRecording && (
            <>
              <button
                onClick={playPreview}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '14px 28px',
                  fontSize: '16px',
                  fontWeight: 600,
                  color: '#374151',
                  background: '#e5e7eb',
                  border: 'none',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  transition: 'transform 0.2s',
                }}
              >
                {isPlaying ? <Pause size={20} /> : <Play size={20} />}
                {isPlaying ? '暂停预览' : '预览'}
              </button>

              <button
                onClick={resetRecording}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '14px 28px',
                  fontSize: '16px',
                  fontWeight: 600,
                  color: '#374151',
                  background: '#e5e7eb',
                  border: 'none',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  transition: 'transform 0.2s',
                }}
              >
                <RotateCcw size={20} />
                重录
              </button>
            </>
          )}
        </div>

        {(isRecording || transcript) && (
          <div style={{
            marginBottom: '24px',
          }}>
            <h3 style={{
              fontSize: '14px',
              fontWeight: 600,
              color: '#6b7280',
              marginBottom: '12px',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
              实时转录
            </h3>
            <div style={{
              background: '#f9fafb',
              borderRadius: '12px',
              padding: '20px',
              minHeight: '120px',
              border: '1px solid #e5e7eb',
            }}>
              <p style={{
                fontSize: '16px',
                lineHeight: 1.7,
                color: '#1f2937',
                whiteSpace: 'pre-wrap',
              }}>
                {transcript || <span style={{ color: '#9ca3af' }}>说话开始转录...</span>}
              </p>
            </div>
          </div>
        )}

        {recordedBlobRef.current && !isRecording && transcript && (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
          }}>
            <button
              onClick={saveNote}
              disabled={isProcessing || savedNote}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '14px 36px',
                fontSize: '16px',
                fontWeight: 600,
                color: 'white',
                background: savedNote ? '#10b981' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: 'none',
                borderRadius: '12px',
                cursor: isProcessing || savedNote ? 'not-allowed' : 'pointer',
                opacity: isProcessing ? 0.7 : 1,
                transition: 'transform 0.2s, box-shadow 0.2s',
                boxShadow: savedNote ? 'none' : '0 4px 14px rgba(102, 126, 234, 0.4)',
              }}
            >
              {isProcessing ? (
                <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
              ) : savedNote ? (
                <Save size={20} />
              ) : (
                <Save size={20} />
              )}
              {isProcessing ? '保存中...' : savedNote ? '已保存 ✓' : '保存笔记'}
            </button>
          </div>
        )}

        {savedNote && (
          <div style={{
            marginTop: '24px',
            padding: '20px',
            background: '#ecfdf5',
            borderRadius: '12px',
            border: '1px solid #a7f3d0',
          }}>
            <h3 style={{
              fontSize: '14px',
              fontWeight: 600,
              color: '#065f46',
              marginBottom: '16px',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
              笔记已保存
            </h3>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'flex-start',
              gap: '16px',
            }}>
              <div>
                <p style={{
                  fontSize: '14px',
                  color: '#047857',
                  marginBottom: '4px',
                }}>
                  <strong>ID:</strong> {savedNote._id}
                </p>
                <p style={{
                  fontSize: '14px',
                  color: '#047857',
                }}>
                  <strong>创建时间:</strong> {new Date(savedNote.createdAt).toLocaleString('zh-CN')}
                </p>
                {savedNote.transcriptionData?.segments?.length > 0 && (
                  <p style={{
                    fontSize: '12px',
                    color: '#059669',
                    marginTop: '8px',
                  }}>
                    ✓ 已获取时间戳数据
                  </p>
                )}
              </div>
              <button
                onClick={goToEdit}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '10px 20px',
                  fontSize: '14px',
                  fontWeight: 600,
                  color: 'white',
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  boxShadow: '0 4px 14px rgba(16, 185, 129, 0.3)',
                  whiteSpace: 'nowrap',
                }}
              >
                <Edit3 size={16} />
                去编辑
              </button>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default Record;