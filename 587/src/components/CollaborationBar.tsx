import React from 'react';
import { Users } from 'lucide-react';
import { useStore } from '../store/useStore';

const CollaborationBar: React.FC = () => {
  const { users, currentUser } = useStore();

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="absolute bottom-4 left-4 bg-white rounded-xl shadow-lg px-4 py-3 flex items-center gap-3 z-20">
      <div className="flex items-center gap-2 text-gray-600">
        <Users size={18} />
        <span className="text-sm font-medium">在线协作</span>
      </div>
      
      <div className="h-6 w-px bg-gray-200" />
      
      <div className="flex items-center">
        <div className="flex -space-x-2">
          {users.slice(0, 5).map((user) => (
            <div
              key={user.id}
              className="relative group"
              title={`${user.name}${user.id === currentUser?.id ? ' (你)' : ''}`}
            >
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-semibold border-2 border-white"
                style={{ backgroundColor: user.color }}
              >
                {getInitials(user.name)}
              </div>
              {user.id === currentUser?.id && (
                <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 rounded-full border-2 border-white" />
              )}
            </div>
          ))}
        </div>
        
        {users.length > 5 && (
          <div className="ml-2 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-600 text-xs font-semibold border-2 border-white">
            +{users.length - 5}
          </div>
        )}
      </div>

      <div className="text-xs text-gray-500">
        {users.length} 人在线
      </div>
    </div>
  );
};

export default CollaborationBar;
