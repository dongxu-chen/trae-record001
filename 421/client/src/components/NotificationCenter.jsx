import React, { useState, useEffect, useRef } from 'react';
import { 
  IconButton, Badge, Popover, List, ListItem, ListItemText, 
  Typography, Box, Divider, Button, Chip
} from '@mui/material';
import NotificationsIcon from '@mui/icons-material/Notifications';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import socketService from '../services/socket';

const NotificationCenter = ({ userId }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const navigate = useNavigate();
  const loadedRef = useRef(false);

  useEffect(() => {
    if (userId && !loadedRef.current) {
      loadedRef.current = true;
      loadNotifications();
      setupSocketListeners();
    }
  }, [userId]);

  const loadNotifications = async () => {
    try {
      const res = await api.get('/api/notifications?limit=20');
      setNotifications(res.data.notifications);
      setUnreadCount(res.data.unreadCount);
    } catch (err) {
      console.error('Load notifications error:', err);
    }
  };

  const setupSocketListeners = () => {
    socketService.on('notification', (notification) => {
      setNotifications(prev => [notification, ...prev]);
      setUnreadCount(prev => prev + 1);
    });

    socketService.on('notification-updated', ({ notificationId, read }) => {
      if (read) {
        setUnreadCount(prev => Math.max(0, prev - 1));
      }
    });
  };

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleNotificationClick = async (notification) => {
    try {
      await api.post(`/api/notifications/${notification._id}/read`);
      setNotifications(prev => 
        prev.map(n => n._id === notification._id ? { ...n, read: true } : n)
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
      
      if (notification.documentId) {
        navigate(`/document/${notification.documentId}`);
      }
      handleClose();
    } catch (err) {
      console.error('Mark read error:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.post('/api/notifications/read-all');
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error('Mark all read error:', err);
    }
  };

  const getNotificationIcon = (type) => {
    const colors = {
      new_revision: 'primary',
      document_submitted: 'info',
      revision_approved: 'success',
      revision_rejected: 'error',
      document_approved: 'success',
      document_rejected: 'error',
      new_comment: 'warning'
    };
    return colors[type] || 'default';
  };

  const getNotificationTypeLabel = (type) => {
    const labels = {
      new_revision: '新修订',
      document_submitted: '提交审核',
      revision_approved: '修订通过',
      revision_rejected: '修订拒绝',
      document_approved: '文档通过',
      document_rejected: '文档拒绝',
      new_comment: '新批注'
    };
    return labels[type] || type;
  };

  const open = Boolean(anchorEl);
  const id = open ? 'notification-popover' : undefined;

  return (
    <>
      <IconButton 
        color="inherit" 
        onClick={handleClick}
        aria-describedby={id}
      >
        <Badge badgeContent={unreadCount} color="error">
          <NotificationsIcon />
        </Badge>
      </IconButton>
      
      <Popover
        id={id}
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        PaperProps={{
          sx: { width: 360, maxHeight: 480 }
        }}
      >
        <Box p={2} display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">通知</Typography>
          {unreadCount > 0 && (
            <Button size="small" onClick={handleMarkAllRead}>
              全部已读
            </Button>
          )}
        </Box>
        <Divider />
        <List sx={{ p: 0 }}>
          {notifications.length === 0 ? (
            <ListItem>
              <ListItemText primary="暂无通知" />
            </ListItem>
          ) : (
            notifications.map((notification) => (
              <React.Fragment key={notification._id}>
                <ListItem
                  button
                  onClick={() => handleNotificationClick(notification)}
                  sx={{
                    bgcolor: notification.read ? 'transparent' : 'action.hover',
                    '&:hover': {
                      bgcolor: notification.read ? 'action.hover' : 'action.selected'
                    }
                  }}
                >
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Chip 
                          label={getNotificationTypeLabel(notification.type)} 
                          color={getNotificationIcon(notification.type)}
                          size="small"
                        />
                        {!notification.read && (
                          <Box 
                            sx={{ 
                              width: 8, 
                              height: 8, 
                              borderRadius: '50%', 
                              bgcolor: 'primary.main' 
                            }} 
                          />
                        )}
                      </Box>
                    }
                    secondary={
                      <>
                        <Typography variant="body2" color="text.primary">
                          {notification.title}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {notification.message}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" display="block">
                          {new Date(notification.createdAt).toLocaleString()}
                        </Typography>
                      </>
                    }
                  />
                </ListItem>
                <Divider variant="inset" component="li" />
              </React.Fragment>
            ))
          )}
        </List>
      </Popover>
    </>
  );
};

export default NotificationCenter;
