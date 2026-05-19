import { withFieldCache } from './cache/FieldCache.js';

export const resolvers = {
  Query: {
    getUser: withFieldCache(
      async (_, { id }, { dataLoaders }) => {
        return dataLoaders.userLoader.load(id);
      },
      'Query',
      'getUser'
    ),
    getUsers: withFieldCache(
      async (_, __, { dataSources }) => {
        return dataSources.userAPI.getUsers();
      },
      'Query',
      'getUsers'
    ),
    getPost: withFieldCache(
      async (_, { id }, { dataLoaders }) => {
        return dataLoaders.postLoader.load(id);
      },
      'Query',
      'getPost'
    ),
    getPosts: withFieldCache(
      async (_, { limit }, { dataSources }) => {
        return dataSources.postAPI.getPosts(limit);
      },
      'Query',
      'getPosts'
    ),
    getComment: withFieldCache(
      async (_, { id }, { dataLoaders }) => {
        return dataLoaders.commentLoader.load(id);
      },
      'Query',
      'getComment'
    ),
    getComments: withFieldCache(
      async (_, __, { dataSources }) => {
        return dataSources.commentAPI.getComments();
      },
      'Query',
      'getComments'
    ),
  },

  Mutation: {
    createUser: async (_, { name, email }, { dataSources, fieldCache, dataLoaders }) => {
      const result = await dataSources.userAPI.createUser(name, email);
      dataLoaders.userLoader.clearAll();
      fieldCache.invalidate('Query', 'getUsers');
      return result;
    },
    createPost: async (_, { title, content, authorId }, { dataSources, fieldCache, dataLoaders }) => {
      const result = await dataSources.postAPI.createPost(title, content, authorId);
      dataLoaders.postLoader.clearAll();
      fieldCache.invalidate('Query', 'getPosts');
      fieldCache.invalidate('User', 'posts');
      return result;
    },
    createComment: async (_, { content, authorId, postId }, { dataSources, fieldCache, dataLoaders }) => {
      const result = await dataSources.commentAPI.createComment(content, authorId, postId);
      dataLoaders.commentLoader.clearAll();
      fieldCache.invalidate('Query', 'getComments');
      fieldCache.invalidate('User', 'comments');
      fieldCache.invalidate('Post', 'comments');
      return result;
    },
  },

  User: {
    posts: withFieldCache(
      async (user, _, { dataLoaders }) => {
        return dataLoaders.postLoader.loadByAuthorId(user.id);
      },
      'User',
      'posts'
    ),
    comments: withFieldCache(
      async (user, _, { dataLoaders }) => {
        return dataLoaders.commentLoader.loadByAuthorId(user.id);
      },
      'User',
      'comments'
    ),
  },

  Post: {
    author: withFieldCache(
      async (post, _, { dataLoaders }) => {
        return dataLoaders.userLoader.load(post.authorId);
      },
      'Post',
      'author'
    ),
    comments: withFieldCache(
      async (post, _, { dataLoaders }) => {
        return dataLoaders.commentLoader.loadByPostId(post.id);
      },
      'Post',
      'comments'
    ),
  },

  Comment: {
    author: withFieldCache(
      async (comment, _, { dataLoaders }) => {
        return dataLoaders.userLoader.load(comment.authorId);
      },
      'Comment',
      'author'
    ),
    post: withFieldCache(
      async (comment, _, { dataLoaders }) => {
        return dataLoaders.postLoader.load(comment.postId);
      },
      'Comment',
      'post'
    ),
  },
};
