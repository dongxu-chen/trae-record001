import { GraphQLJSONObject } from 'graphql-type-json';
import DataLoader from 'dataloader';

export function createResolvers(grpcClientFactory, orchestrator) {
  const createLoaders = () => {
    const userClient = grpcClientFactory.getUserClient();
    const postClient = grpcClientFactory.getPostClient();
    const commentClient = grpcClientFactory.getCommentClient();

    return {
      userLoader: new DataLoader(async (userIds) => {
        const { users } = await userClient.GetUsers({ ids: userIds });
        const userMap = new Map(users.map(u => [u.id, u]));
        return userIds.map(id => userMap.get(id) || null);
      }),

      postLoader: new DataLoader(async (postIds) => {
        const { posts } = await postClient.GetPosts({ ids: postIds });
        const postMap = new Map(posts.map(p => [p.id, p]));
        return postIds.map(id => postMap.get(id) || null);
      }),

      commentLoader: new DataLoader(async (commentIds) => {
        const { comments } = await commentClient.GetComments({ ids: commentIds });
        const commentMap = new Map(comments.map(c => [c.id, c]));
        return commentIds.map(id => commentMap.get(id) || null);
      }),

      postsByAuthorLoader: new DataLoader(async (authorIds) => {
        const results = await Promise.all(
          authorIds.map(id => postClient.GetPostsByAuthor({ authorId: id }))
        );
        return results.map(r => r.posts);
      }),

      commentsByPostLoader: new DataLoader(async (postIds) => {
        const results = await Promise.all(
          postIds.map(id => commentClient.GetCommentsByPost({ postId: id }))
        );
        return results.map(r => r.comments);
      }),
    };
  };

  return {
    JSON: GraphQLJSONObject,

    Query: {
      getUser: async (_, { id }, { loaders }) => {
        return loaders.userLoader.load(id);
      },
      getUsers: async (_, { ids }, { loaders }) => {
        return loaders.userLoader.loadMany(ids);
      },
      listUsers: async (_, { limit = 10, offset = 0 }, { grpcClients }) => {
        return grpcClients.user.ListUsers({ limit, offset });
      },

      getPost: async (_, { id }, { loaders }) => {
        return loaders.postLoader.load(id);
      },
      getPosts: async (_, { ids }, { loaders }) => {
        return loaders.postLoader.loadMany(ids);
      },
      getPostsByAuthor: async (_, { authorId }, { loaders }) => {
        return loaders.postsByAuthorLoader.load(authorId);
      },
      listPosts: async (_, { limit = 10, offset = 0 }, { grpcClients }) => {
        return grpcClients.post.ListPosts({ limit, offset });
      },

      getComment: async (_, { id }, { loaders }) => {
        return loaders.commentLoader.load(id);
      },
      getComments: async (_, { ids }, { loaders }) => {
        return loaders.commentLoader.loadMany(ids);
      },
      getCommentsByPost: async (_, { postId }, { loaders }) => {
        return loaders.commentsByPostLoader.load(postId);
      },
      listComments: async (_, { limit = 10, offset = 0 }, { grpcClients }) => {
        return grpcClients.comment.ListComments({ limit, offset });
      },

      executeWorkflow: async (_, { name, variables }) => {
        if (!orchestrator) {
          return {
            success: false,
            error: 'Orchestrator not available',
            executionTime: 0,
          };
        }
        const startTime = Date.now();
        try {
          const result = await orchestrator.execute({ name, steps: [] }, variables);
          return {
            success: true,
            data: result.variables,
            executionTime: Date.now() - startTime,
          };
        } catch (error) {
          return {
            success: false,
            error: error.message,
            executionTime: Date.now() - startTime,
          };
        }
      },
    },

    Mutation: {
      createUser: async (_, { name, email, role = 'user' }, { grpcClients }) => {
        return grpcClients.user.CreateUser({ name, email, role });
      },
      updateUser: async (_, { id, name, email, role }, { grpcClients }) => {
        return grpcClients.user.UpdateUser({ id, name, email, role });
      },
      deleteUser: async (_, { id }, { grpcClients }) => {
        return grpcClients.user.DeleteUser({ id });
      },

      createPost: async (_, { title, content, authorId }, { grpcClients }) => {
        return grpcClients.post.CreatePost({ title, content, authorId });
      },
      updatePost: async (_, { id, title, content }, { grpcClients }) => {
        return grpcClients.post.UpdatePost({ id, title, content });
      },
      deletePost: async (_, { id }, { grpcClients }) => {
        return grpcClients.post.DeletePost({ id });
      },

      createComment: async (_, { content, postId, authorId }, { grpcClients }) => {
        return grpcClients.comment.CreateComment({ content, postId, authorId });
      },
      updateComment: async (_, { id, content }, { grpcClients }) => {
        return grpcClients.comment.UpdateComment({ id, content });
      },
      deleteComment: async (_, { id }, { grpcClients }) => {
        return grpcClients.comment.DeleteComment({ id });
      },
    },

    User: {
      posts: async (user, _, { loaders }) => {
        return loaders.postsByAuthorLoader.load(user.id);
      },
      comments: async () => [],
    },

    Post: {
      author: async (post, _, { loaders }) => {
        if (!post.authorId) return null;
        return loaders.userLoader.load(post.authorId);
      },
      comments: async (post, _, { loaders }) => {
        return loaders.commentsByPostLoader.load(post.id);
      },
      commentCount: async (post, _, { loaders }) => {
        const comments = await loaders.commentsByPostLoader.load(post.id);
        return comments.length;
      },
    },

    Comment: {
      author: async (comment, _, { loaders }) => {
        if (!comment.authorId) return null;
        return loaders.userLoader.load(comment.authorId);
      },
      post: async (comment, _, { loaders }) => {
        if (!comment.postId) return null;
        return loaders.postLoader.load(comment.postId);
      },
    },
  };
}

export default createResolvers;
