const { Book } = require('../db/mongo');
const { pubsub, NEW_BOOK_ADDED } = require('../pubsub');

module.exports = {
  Query: {
    books: async (parent, { limit = 20, offset = 0 }) => {
      return await Book.find().skip(offset).limit(Math.min(limit, 100));
    },
    book: async (parent, { id }) => {
      return await Book.findById(id);
    }
  },
  Mutation: {
    createBook: async (parent, { title, author, isbn, publishedYear, totalCopies }) => {
      const book = new Book({
        title,
        author,
        isbn,
        publishedYear,
        totalCopies,
        availableCopies: totalCopies
      });
      const savedBook = await book.save();
      await pubsub.publish(NEW_BOOK_ADDED, { newBookAdded: savedBook });
      return savedBook;
    }
  },
  Subscription: {
    newBookAdded: {
      subscribe: () => pubsub.asyncIterator([NEW_BOOK_ADDED])
    }
  }
};
