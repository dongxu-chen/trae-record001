import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  Image,
  StyleSheet,
  FlatList,
  Dimensions,
  TouchableOpacity,
  Animated,
  ActivityIndicator,
  SafeAreaView,
  Modal,
  TextInput,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import VideoPlayer from '../components/VideoPlayer';

const { height: SCREEN_HEIGHT, width: SCREEN_WIDTH } = Dimensions.get('window');

const API_BASE_URL = 'http://localhost:3000/api';
const FEED_API = `${API_BASE_URL}/feed`;
const INTERACT_API = `${API_BASE_URL}/interact`;
const CURRENT_USER_ID = 'current_user';

const formatNumber = (num) => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
};

const VideoCard = ({
  item,
  isActive,
  onLike,
  onUnlike,
  onShare,
  onComment,
  onView,
  onProfile,
  onFollow,
  isLiked,
  isFollowing,
}) => {
  const navigation = useNavigation();
  const [isLikedLocal, setIsLikedLocal] = useState(isLiked);
  const [likesCount, setLikesCount] = useState(item.likes);
  const [isFollowingLocal, setIsFollowingLocal] = useState(isFollowing);
  const [heartAnimation] = useState(new Animated.Value(1));

  useEffect(() => {
    if (isActive && onView) {
      onView(item.id);
    }
  }, [isActive]);

  useEffect(() => {
    setIsLikedLocal(isLiked);
  }, [isLiked]);

  useEffect(() => {
    setIsFollowingLocal(isFollowing);
  }, [isFollowing]);

  const handleLike = () => {
    setIsLikedLocal(!isLikedLocal);
    setLikesCount(prev => (isLikedLocal ? prev - 1 : prev + 1));
    Animated.sequence([
      Animated.timing(heartAnimation, {
        toValue: 1.3,
        duration: 100,
        useNativeDriver: true,
      }),
      Animated.timing(heartAnimation, {
        toValue: 1,
        duration: 100,
        useNativeDriver: true,
      }),
    ]).start();
    if (isLikedLocal && onUnlike) {
      onUnlike(item.id);
    } else if (!isLikedLocal && onLike) {
      onLike(item.id);
    }
  };

  const handleFollow = async () => {
    const newIsFollowing = !isFollowingLocal;
    setIsFollowingLocal(newIsFollowing);
    if (onFollow) {
      onFollow(item.authorId, item.author, newIsFollowing);
    }
  };

  const handlePressProfile = () => {
    if (onProfile) {
      onProfile(item.authorId, item.author);
    } else {
      navigation.navigate('Profile', {
        userId: item.authorId,
        username: item.author,
      });
    }
  };

  return (
    <View style={styles.container}>
      <VideoPlayer
        videoUrl={item.videoUrl}
        shouldPlay={isActive}
      />
      
      <View style={styles.overlay}>
        <View style={styles.rightActions}>
          <View style={styles.actionContainer}>
            <TouchableOpacity onPress={handleLike} style={styles.iconButton}>
              <Animated.View style={{ transform: [{ scale: heartAnimation }] }}>
                <Ionicons
                  name={isLikedLocal ? 'heart' : 'heart-outline'}
                  size={35}
                  color={isLikedLocal ? '#ff2d55' : '#ffffff'}
                />
              </Animated.View>
            </TouchableOpacity>
            <Text style={styles.actionText}>{formatNumber(likesCount)}</Text>
          </View>

          <View style={styles.actionContainer}>
            <TouchableOpacity
              onPress={() => onComment && onComment(item.id, item.comments)}
              style={styles.iconButton}
            >
              <Ionicons
                name="chatbubble-outline"
                size={35}
                color="#ffffff"
              />
            </TouchableOpacity>
            <Text style={styles.actionText}>{formatNumber(item.comments)}</Text>
          </View>

          <View style={styles.actionContainer}>
            <TouchableOpacity
              onPress={() => onShare && onShare(item.id)}
              style={styles.iconButton}
            >
              <Ionicons
                name="share-social-outline"
                size={35}
                color="#ffffff"
              />
            </TouchableOpacity>
            <Text style={styles.actionText}>{formatNumber(item.shares)}</Text>
          </View>

          <View style={styles.profileContainer}>
            <TouchableOpacity
              onPress={handlePressProfile}
              activeOpacity={0.7}
            >
              <View style={styles.avatarWrapper}>
                <Ionicons
                  name="person-circle"
                  size={50}
                  color="#ffffff"
                />
              </View>
            </TouchableOpacity>
            {!isFollowingLocal ? (
              <TouchableOpacity
                onPress={handleFollow}
                style={styles.followButton}
              >
                <Ionicons
                  name="add-circle"
                  size={25}
                  color="#ff2d55"
                />
              </TouchableOpacity>
            ) : (
              <TouchableOpacity
                onPress={handleFollow}
                style={styles.followingButton}
              >
                <Ionicons
                  name="checkmark-circle"
                  size={25}
                  color="#ffffff"
                />
              </TouchableOpacity>
            )}
          </View>
        </View>

        <View style={styles.bottomInfo}>
          <TouchableOpacity onPress={handlePressProfile}>
            <Text style={styles.username}>@{item.author}</Text>
          </TouchableOpacity>
          <Text style={styles.description}>{item.description}</Text>
          <View style={styles.soundContainer}>
            <MaterialCommunityIcons
              name="music-note"
              size={18}
              color="#ffffff"
            />
            <Text style={styles.soundText}>Original Sound - {item.author}</Text>
          </View>
        </View>
      </View>
    </View>
  );
};

const CommentModal = ({ visible, videoId, onClose, onSend }) => {
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false);
  const [comments, setComments] = useState([]);

  useEffect(() => {
    if (visible && videoId) {
      fetchComments();
    }
  }, [visible, videoId]);

  const fetchComments = async () => {
    try {
      const response = await fetch(`${INTERACT_API}/comments/${videoId}`);
      const data = await response.json();
      setComments(data.comments || []);
    } catch (error) {
      console.error('Failed to fetch comments:', error);
    }
  };

  const handleSend = async () => {
    if (!comment.trim() || loading) return;
    
    setLoading(true);
    try {
      const response = await fetch(`${INTERACT_API}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: CURRENT_USER_ID,
          videoId,
          content: comment.trim(),
        }),
      });
      const data = await response.json();
      
      if (data.success) {
        setComment('');
        await fetchComments();
        if (onSend) {
          onSend();
        }
      }
    } catch (error) {
      console.error('Failed to send comment:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={true}
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.modalContainer}
      >
        <View style={styles.modalContent}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Comments</Text>
            <TouchableOpacity onPress={onClose}>
              <Ionicons name="close" size={28} color="#fff" />
            </TouchableOpacity>
          </View>

          <FlatList
            data={comments}
            keyExtractor={(item) => item.id}
            style={styles.commentsList}
            renderItem={({ item }) => (
              <View style={styles.commentItem}>
                <View style={styles.commentAvatar}>
                  <Ionicons name="person-circle" size={40} color="#ff2d55" />
                </View>
                <View style={styles.commentContent}>
                  <Text style={styles.commentUser}>@{item.userId}</Text>
                  <Text style={styles.commentText}>{item.content}</Text>
                </View>
              </View>
            )}
            ListEmptyComponent={
              <View style={styles.emptyComments}>
                <Text style={styles.emptyCommentsText}>No comments yet</Text>
              </View>
            }
          />

          <View style={styles.commentInputContainer}>
            <TextInput
              style={styles.commentInput}
              placeholder="Add a comment..."
              placeholderTextColor="#666"
              value={comment}
              onChangeText={setComment}
              multiline
              maxLength={500}
            />
            <TouchableOpacity
              style={[styles.sendButton, !comment.trim() && styles.sendButtonDisabled]}
              onPress={handleSend}
              disabled={!comment.trim() || loading}
            >
              {loading ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text style={styles.sendButtonText}>Post</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
};

const Feed = () => {
  const navigation = useNavigation();
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [likedVideos, setLikedVideos] = useState(new Set());
  const [viewedVideos, setViewedVideos] = useState(new Set());
  const [followingUsers, setFollowingUsers] = useState(new Set());
  const [commentModalVisible, setCommentModalVisible] = useState(false);
  const [currentCommentVideoId, setCurrentCommentVideoId] = useState(null);
  const flatListRef = useRef(null);
  const viewabilityConfig = useRef({
    itemVisiblePercentThreshold: 80,
  });

  const fetchFeed = useCallback(async (excludedIds = []) => {
    try {
      const params = new URLSearchParams({
        userId: CURRENT_USER_ID,
        limit: '10',
        ...(excludedIds.length > 0 && { excludedIds: excludedIds.join(',') }),
      });
      const response = await fetch(`${FEED_API}?${params}`);
      const data = await response.json();
      return data.videos || [];
    } catch (error) {
      console.error('Failed to fetch feed:', error);
      return [];
    }
  }, []);

  const loadInitialFeed = useCallback(async () => {
    setLoading(true);
    setVideos([]);
    setViewedVideos(new Set());
    setLikedVideos(new Set());
    setCurrentIndex(0);

    try {
      const followingRes = await fetch(`${INTERACT_API}/following/${CURRENT_USER_ID}`);
      const followingData = await followingRes.json();
      setFollowingUsers(new Set(followingData.followingIds || []));
    } catch (error) {
      console.error('Failed to fetch following:', error);
    }

    const newVideos = await fetchFeed();
    setVideos(newVideos);
    setLoading(false);
  }, [fetchFeed]);

  const loadMoreFeed = useCallback(async () => {
    if (loadingMore) return;
    setLoadingMore(true);
    const currentVideoIds = videos.map(v => v.id);
    const excludedIds = Array.from(new Set([...currentVideoIds, ...Array.from(viewedVideos)]));
    const newVideos = await fetchFeed(excludedIds);
    const seenIds = new Set(currentVideoIds);
    const uniqueNewVideos = newVideos.filter(v => !seenIds.has(v.id));
    if (uniqueNewVideos.length > 0) {
      setVideos(prev => [...prev, ...uniqueNewVideos]);
    }
    setLoadingMore(false);
  }, [fetchFeed, loadingMore, videos, viewedVideos]);

  useEffect(() => {
    loadInitialFeed();
  }, [loadInitialFeed]);

  const onViewableItemsChanged = useCallback(({ viewableItems }) => {
    if (viewableItems.length > 0) {
      const index = viewableItems[0].index;
      setCurrentIndex(index);
      const videoId = viewableItems[0].item.id;
      setViewedVideos(prev => {
        if (prev.has(videoId)) {
          return prev;
        }
        return new Set([...prev, videoId]);
      });
    }
  }, []);

  const handleLike = async (videoId) => {
    setLikedVideos(prev => new Set([...prev, videoId]));
    try {
      await fetch(`${INTERACT_API}/like`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: CURRENT_USER_ID,
          videoId,
        }),
      });
    } catch (error) {
      console.error('Failed to like:', error);
    }
  };

  const handleUnlike = async (videoId) => {
    setLikedVideos(prev => {
      const newSet = new Set(prev);
      newSet.delete(videoId);
      return newSet;
    });
    try {
      await fetch(`${INTERACT_API}/unlike`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: CURRENT_USER_ID,
          videoId,
        }),
      });
    } catch (error) {
      console.error('Failed to unlike:', error);
    }
  };

  const handleComment = (videoId, commentCount) => {
    setCurrentCommentVideoId(videoId);
    setCommentModalVisible(true);
  };

  const handleShare = async (videoId) => {
    try {
      await fetch(`${INTERACT_API}/comments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: CURRENT_USER_ID,
          videoId,
          content: 'Shared',
        }),
      });
    } catch (error) {
      console.error('Failed to share:', error);
    }
  };

  const handleView = async (videoId) => {
    try {
      await fetch(`${FEED_API}/interact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          userId: CURRENT_USER_ID,
          videoId,
          interactionType: 'view',
        }),
      });
    } catch (error) {
      console.error('Failed to record view:', error);
    }
  };

  const handleFollow = async (authorId, authorName, isFollowing) => {
    const endpoint = isFollowing ? 'follow' : 'unfollow';
    setFollowingUsers(prev => {
      const newSet = new Set(prev);
      if (isFollowing) {
        newSet.add(authorId);
      } else {
        newSet.delete(authorId);
      }
      return newSet;
    });

    try {
      await fetch(`${INTERACT_API}/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          followerId: CURRENT_USER_ID,
          followingId: authorId,
        }),
      });
    } catch (error) {
      console.error(`Failed to ${endpoint}:`, error);
      setFollowingUsers(prev => {
        const newSet = new Set(prev);
        if (!isFollowing) {
          newSet.add(authorId);
        } else {
          newSet.delete(authorId);
        }
        return newSet;
      });
    }
  };

  const handleProfile = (userId, username) => {
    navigation.navigate('Profile', {
      userId,
      username,
    });
  };

  const getItemLayout = (data, index) => ({
    length: SCREEN_HEIGHT,
    offset: SCREEN_HEIGHT * index,
    index,
  });

  const keyExtractor = (item) => item.id;

  const renderItem = ({ item, index }) => (
    <VideoCard
      item={item}
      isActive={index === currentIndex}
      onLike={handleLike}
      onUnlike={handleUnlike}
      onComment={handleComment}
      onShare={handleShare}
      onView={handleView}
      onProfile={handleProfile}
      onFollow={handleFollow}
      isLiked={likedVideos.has(item.id)}
      isFollowing={followingUsers.has(item.authorId)}
    />
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#ff2d55" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>For You</Text>
        <Text style={styles.headerText}>Following</Text>
        <TouchableOpacity
          style={styles.profileButton}
          onPress={() => navigation.navigate('Profile', {
            userId: CURRENT_USER_ID,
            username: 'Me',
          })}
        >
          <Ionicons name="person" size={24} color="#fff" />
        </TouchableOpacity>
      </View>
      <FlatList
        ref={flatListRef}
        data={videos}
        renderItem={renderItem}
        keyExtractor={keyExtractor}
        getItemLayout={getItemLayout}
        pagingEnabled
        showsVerticalScrollIndicator={false}
        onViewableItemsChanged={onViewableItemsChanged}
        viewabilityConfig={viewabilityConfig.current}
        onEndReached={loadMoreFeed}
        onEndReachedThreshold={0.5}
        decelerationRate="fast"
        ListFooterComponent={
          loadingMore ? (
            <View style={styles.footerLoader}>
              <ActivityIndicator size="large" color="#ff2d55" />
            </View>
          ) : null
        }
      />
      <CommentModal
        visible={commentModalVisible}
        videoId={currentCommentVideoId}
        onClose={() => setCommentModalVisible(false)}
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#000000',
  },
  container: {
    height: SCREEN_HEIGHT,
    width: SCREEN_WIDTH,
  },
  header: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 50,
    paddingBottom: 10,
    zIndex: 10,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#ffffff',
    marginRight: 20,
  },
  headerText: {
    fontSize: 18,
    color: 'rgba(255, 255, 255, 0.5)',
  },
  profileButton: {
    position: 'absolute',
    right: 15,
    top: 48,
    padding: 5,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    paddingBottom: 50,
    paddingHorizontal: 15,
  },
  bottomInfo: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  username: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 5,
  },
  description: {
    fontSize: 14,
    color: '#ffffff',
    marginBottom: 5,
  },
  soundContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  soundText: {
    fontSize: 13,
    color: '#ffffff',
    marginLeft: 5,
  },
  rightActions: {
    alignItems: 'center',
  },
  actionContainer: {
    marginBottom: 20,
    alignItems: 'center',
  },
  iconButton: {
    padding: 5,
  },
  actionText: {
    fontSize: 12,
    color: '#ffffff',
    marginTop: 3,
  },
  profileContainer: {
    alignItems: 'center',
    marginTop: 10,
  },
  avatarWrapper: {
    width: 50,
    height: 50,
    borderRadius: 25,
    borderWidth: 2,
    borderColor: '#ffffff',
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
  },
  followButton: {
    position: 'absolute',
    bottom: -12,
  },
  followingButton: {
    position: 'absolute',
    bottom: -12,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#000000',
  },
  footerLoader: {
    paddingVertical: 20,
    alignItems: 'center',
  },
  modalContainer: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  modalContent: {
    height: SCREEN_HEIGHT * 0.75,
    backgroundColor: '#1a1a1a',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 15,
    borderBottomWidth: 0.5,
    borderBottomColor: '#333',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  commentsList: {
    flex: 1,
    paddingHorizontal: 15,
  },
  commentItem: {
    flexDirection: 'row',
    paddingVertical: 12,
    borderBottomWidth: 0.5,
    borderBottomColor: '#333',
  },
  commentAvatar: {
    marginRight: 12,
  },
  commentContent: {
    flex: 1,
  },
  commentUser: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  commentText: {
    fontSize: 14,
    color: '#ccc',
  },
  emptyComments: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyCommentsText: {
    color: '#666',
    fontSize: 16,
  },
  commentInputContainer: {
    flexDirection: 'row',
    padding: 15,
    borderTopWidth: 0.5,
    borderTopColor: '#333',
    backgroundColor: '#1a1a1a',
  },
  commentInput: {
    flex: 1,
    backgroundColor: '#333',
    borderRadius: 20,
    paddingHorizontal: 15,
    paddingVertical: 10,
    color: '#fff',
    maxHeight: 100,
  },
  sendButton: {
    marginLeft: 10,
    backgroundColor: '#ff2d55',
    paddingHorizontal: 20,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 20,
  },
  sendButtonDisabled: {
    backgroundColor: '#666',
  },
  sendButtonText: {
    color: '#fff',
    fontWeight: 'bold',
  },
});

export default Feed;
