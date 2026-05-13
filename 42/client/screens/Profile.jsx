import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  SafeAreaView,
  Image,
  Dimensions,
  Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation, useRoute } from '@react-navigation/native';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const API_BASE_URL = 'http://localhost:3000/api';
const CURRENT_USER_ID = 'current_user';

const Profile = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { userId = CURRENT_USER_ID, username = 'User' } = route.params || {};
  
  const [activeTab, setActiveTab] = useState('videos');
  const [likedVideos, setLikedVideos] = useState([]);
  const [followers, setFollowers] = useState([]);
  const [following, setFollowing] = useState([]);
  const [isFollowing, setIsFollowing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    videos: 0,
    followers: 0,
    following: 0,
    likes: 0,
  });

  const fetchProfileData = useCallback(async () => {
    setLoading(true);
    try {
      const [likedRes, followersRes, followingRes, followStatusRes] = await Promise.all([
        fetch(`${API_BASE_URL}/interact/likes/videos/${userId}`),
        fetch(`${API_BASE_URL}/interact/followers/${userId}`),
        fetch(`${API_BASE_URL}/interact/following/${userId}`),
        fetch(`${API_BASE_URL}/interact/status/follow/${CURRENT_USER_ID}/${userId}`),
      ]);

      const likedData = await likedRes.json();
      const followersData = await followersRes.json();
      const followingData = await followingRes.json();
      const followStatusData = await followStatusRes.json();

      setLikedVideos(likedData.videos || []);
      setFollowers(followersData.followerIds || []);
      setFollowing(followingData.followingIds || []);
      setIsFollowing(followStatusData.isFollowing || false);
      setStats({
        videos: likedData.videos?.length || 0,
        followers: followersData.count || 0,
        following: followingData.count || 0,
        likes: likedData.videos?.reduce((acc, v) => acc + (v.likes || 0), 0) || 0,
      });
    } catch (error) {
      console.error('Failed to fetch profile data:', error);
      Alert.alert('Error', 'Failed to load profile data');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    fetchProfileData();
  }, [fetchProfileData]);

  const handleFollow = async () => {
    try {
      const endpoint = isFollowing ? 'unfollow' : 'follow';
      const response = await fetch(`${API_BASE_URL}/interact/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          followerId: CURRENT_USER_ID,
          followingId: userId,
        }),
      });
      const data = await response.json();
      
      if (data.success) {
        setIsFollowing(!isFollowing);
        setStats(prev => ({
          ...prev,
          followers: isFollowing ? prev.followers - 1 : prev.followers + 1,
        }));
      }
    } catch (error) {
      console.error('Follow error:', error);
      Alert.alert('Error', 'Failed to update follow status');
    }
  };

  const navigateToUser = (targetUserId, targetUsername) => {
    if (targetUserId === userId) return;
    navigation.push('Profile', {
      userId: targetUserId,
      username: targetUsername || targetUserId,
    });
  };

  const renderVideoItem = ({ item }) => (
    <TouchableOpacity
      style={styles.videoGridItem}
      activeOpacity={0.7}
    >
      <View style={styles.videoPlaceholder}>
        <Ionicons name="play-circle" size={40} color="rgba(255,255,255,0.8)" />
      </View>
      <View style={styles.videoInfo}>
        <Ionicons name="heart" size={12} color="#fff" />
        <Text style={styles.videoLikes}>{item.likes || 0}</Text>
      </View>
    </TouchableOpacity>
  );

  const renderUserItem = ({ item, type }) => (
    <TouchableOpacity
      style={styles.userListItem}
      onPress={() => navigateToUser(item, item)}
      activeOpacity={0.7}
    >
      <View style={styles.userAvatar}>
        <Ionicons name="person-circle" size={50} color="#ff2d55" />
      </View>
      <View style={styles.userInfo}>
        <Text style={styles.userName}>@{item}</Text>
        <Text style={styles.userDesc}>{type === 'followers' ? 'Follower' : 'Following'}</Text>
      </View>
      <TouchableOpacity style={styles.smallFollowButton}>
        <Text style={styles.smallFollowText}>Follow</Text>
      </TouchableOpacity>
    </TouchableOpacity>
  );

  const renderContent = () => {
    if (activeTab === 'videos') {
      if (likedVideos.length === 0) {
        return (
          <View style={styles.emptyContainer}>
            <Ionicons name="videocam-off" size={60} color="#666" />
            <Text style={styles.emptyText}>No videos yet</Text>
          </View>
        );
      }
      return (
        <FlatList
          data={likedVideos}
          renderItem={renderVideoItem}
          keyExtractor={(item) => item.id}
          numColumns={3}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.gridContainer}
        />
      );
    }

    if (activeTab === 'followers') {
      if (followers.length === 0) {
        return (
          <View style={styles.emptyContainer}>
            <Ionicons name="people" size={60} color="#666" />
            <Text style={styles.emptyText}>No followers yet</Text>
          </View>
        );
      }
      return (
        <FlatList
          data={followers}
          renderItem={(props) => renderUserItem({ ...props, type: 'followers' })}
          keyExtractor={(item) => item}
          showsVerticalScrollIndicator={false}
        />
      );
    }

    if (activeTab === 'following') {
      if (following.length === 0) {
        return (
          <View style={styles.emptyContainer}>
            <Ionicons name="people-outline" size={60} color="#666" />
            <Text style={styles.emptyText}>Not following anyone</Text>
          </View>
        );
      }
      return (
        <FlatList
          data={following}
          renderItem={(props) => renderUserItem({ ...props, type: 'following' })}
          keyExtractor={(item) => item}
          showsVerticalScrollIndicator={false}
        />
      );
    }

    return null;
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#ff2d55" />
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backButton}
        >
          <Ionicons name="arrow-back" size={28} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{username}</Text>
        <TouchableOpacity style={styles.moreButton}>
          <Ionicons name="ellipsis-horizontal" size={28} color="#fff" />
        </TouchableOpacity>
      </View>

      <View style={styles.profileHeader}>
        <View style={styles.avatarContainer}>
          <Ionicons name="person-circle" size={100} color="#ff2d55" />
        </View>
        
        <View style={styles.statsRow}>
          <View style={styles.statItem}>
            <Text style={styles.statNumber}>{stats.videos}</Text>
            <Text style={styles.statLabel}>Videos</Text>
          </View>
          <TouchableOpacity
            style={styles.statItem}
            onPress={() => setActiveTab('followers')}
          >
            <Text style={styles.statNumber}>{stats.followers}</Text>
            <Text style={styles.statLabel}>Followers</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.statItem}
            onPress={() => setActiveTab('following')}
          >
            <Text style={styles.statNumber}>{stats.following}</Text>
            <Text style={styles.statLabel}>Following</Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.bioSection}>
        <Text style={styles.bioName}>@{username}</Text>
        <Text style={styles.bioText}>Welcome to my profile!</Text>
      </View>

      <View style={styles.actionButtons}>
        {userId !== CURRENT_USER_ID ? (
          <TouchableOpacity
            style={[styles.followButton, isFollowing && styles.followingButton]}
            onPress={handleFollow}
            activeOpacity={0.7}
          >
            <Text style={[styles.followButtonText, isFollowing && styles.followingButtonText]}>
              {isFollowing ? 'Following' : 'Follow'}
            </Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity style={styles.editButton}>
            <Text style={styles.editButtonText}>Edit Profile</Text>
          </TouchableOpacity>
        )}
      </View>

      <View style={styles.tabsContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'videos' && styles.activeTab]}
          onPress={() => setActiveTab('videos')}
        >
          <Ionicons
            name={activeTab === 'videos' ? 'grid' : 'grid-outline'}
            size={28}
            color={activeTab === 'videos' ? '#ff2d55' : '#666'}
          />
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'followers' && styles.activeTab]}
          onPress={() => setActiveTab('followers')}
        >
          <Ionicons
            name={activeTab === 'followers' ? 'people' : 'people-outline'}
            size={28}
            color={activeTab === 'followers' ? '#ff2d55' : '#666'}
          />
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'following' && styles.activeTab]}
          onPress={() => setActiveTab('following')}
        >
          <Ionicons
            name={activeTab === 'following' ? 'heart' : 'heart-outline'}
            size={28}
            color={activeTab === 'following' ? '#ff2d55' : '#666'}
          />
        </TouchableOpacity>
      </View>

      <View style={styles.contentContainer}>{renderContent()}</View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#000',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 15,
    paddingVertical: 10,
  },
  backButton: {
    padding: 5,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
  },
  moreButton: {
    padding: 5,
  },
  profileHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 15,
  },
  avatarContainer: {
    marginRight: 30,
  },
  statsRow: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  statItem: {
    alignItems: 'center',
  },
  statNumber: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  bioSection: {
    paddingHorizontal: 20,
    paddingBottom: 10,
  },
  bioName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 5,
  },
  bioText: {
    fontSize: 14,
    color: '#ccc',
  },
  actionButtons: {
    paddingHorizontal: 20,
    paddingBottom: 15,
  },
  followButton: {
    backgroundColor: '#ff2d55',
    paddingVertical: 10,
    borderRadius: 5,
    alignItems: 'center',
  },
  followingButton: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: '#666',
  },
  followButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  followingButtonText: {
    color: '#fff',
  },
  editButton: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: '#666',
    paddingVertical: 10,
    borderRadius: 5,
    alignItems: 'center',
  },
  editButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  tabsContainer: {
    flexDirection: 'row',
    borderTopWidth: 0.5,
    borderTopColor: '#333',
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 12,
  },
  activeTab: {
    borderBottomWidth: 2,
    borderBottomColor: '#ff2d55',
  },
  contentContainer: {
    flex: 1,
  },
  gridContainer: {
    padding: 1,
  },
  videoGridItem: {
    width: SCREEN_WIDTH / 3 - 2,
    height: 180,
    margin: 1,
    backgroundColor: '#1a1a1a',
    position: 'relative',
  },
  videoPlaceholder: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#1a1a1a',
  },
  videoInfo: {
    position: 'absolute',
    bottom: 5,
    left: 5,
    flexDirection: 'row',
    alignItems: 'center',
  },
  videoLikes: {
    fontSize: 12,
    color: '#fff',
    marginLeft: 3,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    color: '#666',
    fontSize: 16,
    marginTop: 10,
  },
  userListItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 15,
    paddingVertical: 12,
    borderBottomWidth: 0.5,
    borderBottomColor: '#333',
  },
  userAvatar: {
    marginRight: 15,
  },
  userInfo: {
    flex: 1,
  },
  userName: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#fff',
  },
  userDesc: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  smallFollowButton: {
    backgroundColor: '#ff2d55',
    paddingHorizontal: 15,
    paddingVertical: 6,
    borderRadius: 5,
  },
  smallFollowText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
  },
});

export default Profile;
