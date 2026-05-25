import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { v4 as uuidv4 } from 'uuid';
import useSocket from '../hooks/useSocket';
import useMeetingStore from '../store/useMeetingStore';
import { VideoIcon, UsersIcon, MicIcon, MonitorIcon } from '../components/icons';

const LobbyPage = () => {
  const navigate = useNavigate();
  const { roomId: urlRoomId } = useParams();
  const { connect, createRoom, joinRoom } = useSocket();
  
  const { setUser, setRoomId } = useMeetingStore();
  const [name, setName] = useState('');
  const [roomId, setRoomIdInput] = useState(urlRoomId || '');
  const [isCreating, setIsCreating] = useState(false);
  const [isJoining, setIsJoining] = useState(false);
  const [error, setError] = useState('');
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const socket = connect();
    if (socket) {
      socket.on('connect', () => {
        setIsConnected(true);
      });
      socket.on('disconnect', () => {
        setIsConnected(false);
      });
    }
  }, [connect]);

  useEffect(() => {
    if (urlRoomId) {
      setRoomIdInput(urlRoomId);
    }
  }, [urlRoomId]);

  const generateRandomName = () => {
    const names = ['张三', '李四', '王五', '赵六', '陈七', '周八', '吴九', '郑十'];
    return names[Math.floor(Math.random() * names.length)];
  };

  const handleCreateRoom = async () => {
    if (!name.trim()) {
      setError('请输入您的姓名');
      return;
    }

    setIsCreating(true);
    setError('');

    try {
      const user = {
        id: uuidv4(),
        name: name.trim(),
        avatar: null
      };

      const response = await createRoom(user);
      
      if (response?.success) {
        setUser(user);
        setRoomId(response.roomId);
        navigate(`/meeting/${response.roomId}`);
      } else {
        setError(response?.error || '创建房间失败');
      }
    } catch (err) {
      setError('创建房间失败，请重试');
    } finally {
      setIsCreating(false);
    }
  };

  const handleJoinRoom = async () => {
    if (!name.trim()) {
      setError('请输入您的姓名');
      return;
    }

    if (!roomId.trim()) {
      setError('请输入房间号');
      return;
    }

    setIsJoining(true);
    setError('');

    try {
      const user = {
        id: uuidv4(),
        name: name.trim(),
        avatar: null
      };

      const response = await joinRoom(roomId.trim().toUpperCase(), user);
      
      if (response?.success) {
        setUser(user);
        setRoomId(response.roomId);
        navigate(`/meeting/${response.roomId}`);
      } else {
        setError(response?.error || '加入房间失败');
      }
    } catch (err) {
      setError('加入房间失败，请重试');
    } finally {
      setIsJoining(false);
    }
  };

  const handleQuickJoin = () => {
    if (!name.trim()) {
      setName(generateRandomName());
    }
    handleCreateRoom();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary-500/20 mb-4">
            <VideoIcon className="w-8 h-8 text-primary-400" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">视频会议</h1>
          <p className="text-slate-400">高质量的多人实时视频会议</p>
        </div>

        <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700">
          {error && (
            <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-300 mb-2">
              您的姓名
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="请输入您的姓名"
              className="w-full bg-slate-700/50 text-white placeholder-slate-400 rounded-xl px-4 py-3 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
            />
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-300 mb-2">
              房间号
            </label>
            <input
              type="text"
              value={roomId}
              onChange={(e) => setRoomIdInput(e.target.value.toUpperCase())}
              placeholder="输入房间号加入会议"
              className="w-full bg-slate-700/50 text-white placeholder-slate-400 rounded-xl px-4 py-3 border border-slate-600 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
            />
          </div>

          <div className="space-y-3">
            <button
              onClick={handleCreateRoom}
              disabled={isCreating || !isConnected}
              className="w-full bg-primary-500 hover:bg-primary-600 disabled:bg-slate-600 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-xl transition-all flex items-center justify-center gap-2"
            >
              <UsersIcon className="w-5 h-5" />
              {isCreating ? '创建中...' : '创建新会议'}
            </button>

            <button
              onClick={handleJoinRoom}
              disabled={isJoining || !isConnected || !roomId.trim()}
              className="w-full bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-xl transition-all"
            >
              {isJoining ? '加入中...' : '加入会议'}
            </button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-slate-600" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-4 bg-slate-800/50 text-slate-400">或者</span>
              </div>
            </div>

            <button
              onClick={handleQuickJoin}
              disabled={!isConnected}
              className="w-full bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 disabled:from-slate-600 disabled:to-slate-600 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-xl transition-all"
            >
              快速加入（随机姓名）
            </button>
          </div>
        </div>

        <div className="mt-8 grid grid-cols-3 gap-4">
          <div className="text-center p-4">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-500/20 mb-2">
              <UsersIcon className="w-6 h-6 text-blue-400" />
            </div>
            <p className="text-sm text-slate-400">最多50人</p>
          </div>
          <div className="text-center p-4">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-green-500/20 mb-2">
              <MicIcon className="w-6 h-6 text-green-400" />
            </div>
            <p className="text-sm text-slate-400">回声消除</p>
          </div>
          <div className="text-center p-4">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-purple-500/20 mb-2">
              <MonitorIcon className="w-6 h-6 text-purple-400" />
            </div>
            <p className="text-sm text-slate-400">屏幕共享</p>
          </div>
        </div>

        <div className="mt-6 text-center">
          <p className="text-xs text-slate-500">
            {isConnected ? (
              <span className="text-green-400">● 已连接到服务器</span>
            ) : (
              <span className="text-yellow-400">● 连接中...</span>
            )}
          </p>
        </div>
      </div>
    </div>
  );
};

export default LobbyPage;
