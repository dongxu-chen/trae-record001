import NextAuth from 'next-auth';
import CredentialsProvider from 'next-auth/providers/credentials';
import { connectDB, User } from '../../../lib/db';

export default NextAuth({
  providers: [
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        username: { label: '用户名', type: 'text', placeholder: '请输入用户名' },
        password: { label: '密码', type: 'password', placeholder: '请输入密码' },
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) {
          throw new Error('请填写用户名和密码');
        }

        await connectDB();

        let user = await User.findOne({ username: credentials.username }).lean();

        if (!user) {
          user = await User.create({
            username: credentials.username,
            name: credentials.username,
            password: credentials.password,
          });
        } else {
          if (user.password !== credentials.password) {
            throw new Error('密码错误');
          }
        }

        return {
          id: user._id.toString(),
          name: user.name,
          username: user.username,
          email: user.email,
        };
      },
    }),
  ],
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60,
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        token.username = user.username;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id;
        session.user.username = token.username;
      }
      return session;
    },
  },
  pages: {
    signIn: '/',
  },
  secret: process.env.NEXTAUTH_SECRET || 'development-secret-change-in-production',
});
