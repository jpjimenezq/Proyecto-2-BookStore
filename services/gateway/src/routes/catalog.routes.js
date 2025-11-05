const express = require('express');
const router = express.Router();
const grpcClient = require('../clients/grpc-client');
const { optionalAuth, authenticateToken, requireAdmin } = require('../middleware/auth');

/**
 * GET /api/catalog/books
 * List books with pagination and filters
 */
router.get('/books', optionalAuth, async (req, res, next) => {
  try {
    const {
      page = 1,
      page_size = 10,
      category,
      author,
      active_only = true,
      min_price,
      max_price
    } = req.query;

    const request = {
      pagination: {
        page: parseInt(page),
        page_size: parseInt(page_size)
      },
      active_only: active_only === 'true' || active_only === true
    };

    if (category) request.category = category;
    if (author) request.author = author;
    if (min_price) request.min_price = parseFloat(min_price);
    if (max_price) request.max_price = parseFloat(max_price);

    const response = await grpcClient.call('catalog', 'ListBooks', request);

    // Convert Money objects to simple numbers for REST response
    const books = response.books.map(book => ({
      sku: book.sku,
      title: book.title,
      author: book.author,
      price: book.price ? {
        amount: book.price.amount / 100, // Convert from cents
        currency: book.price.currency
      } : null,
      category: book.category,
      description: book.description,
      active: book.active,
      stock: book.stock,
      created_at: book.created_at,
      updated_at: book.updated_at
    }));

    res.json({
      books,
      pagination: {
        page: response.pagination.page,
        page_size: response.pagination.page_size,
        total: response.pagination.total,
        total_pages: response.pagination.total_pages
      }
    });
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/catalog/books/:sku
 * Get a specific book by SKU
 */
router.get('/books/:sku', optionalAuth, async (req, res, next) => {
  try {
    const { sku } = req.params;

    const response = await grpcClient.call('catalog', 'GetBook', { sku });

    const book = {
      sku: response.book.sku,
      title: response.book.title,
      author: response.book.author,
      price: response.book.price ? {
        amount: response.book.price.amount / 100,
        currency: response.book.price.currency
      } : null,
      category: response.book.category,
      description: response.book.description,
      active: response.book.active,
      stock: response.book.stock,
      created_at: response.book.created_at,
      updated_at: response.book.updated_at
    };

    res.json(book);
  } catch (error) {
    next(error);
  }
});

/**
 * GET /api/catalog/books/search
 * Search books by query
 */
router.get('/books/search', optionalAuth, async (req, res, next) => {
  try {
    const {
      query,
      page = 1,
      page_size = 10,
      category
    } = req.query;

    if (!query) {
      return res.status(400).json({
        error: 'Validation error',
        message: 'Search query is required'
      });
    }

    const request = {
      query,
      pagination: {
        page: parseInt(page),
        page_size: parseInt(page_size)
      }
    };

    if (category) request.category = category;

    const response = await grpcClient.call('catalog', 'SearchBooks', request);

    const books = response.books.map(book => ({
      sku: book.sku,
      title: book.title,
      author: book.author,
      price: book.price ? {
        amount: book.price.amount / 100,
        currency: book.price.currency
      } : null,
      category: book.category,
      description: book.description,
      active: book.active
    }));

    res.json({
      books,
      pagination: response.pagination,
      max_score: response.max_score
    });
  } catch (error) {
    next(error);
  }
});

/**
 * POST /api/catalog/books
 * Create a new book (Admin only)
 * Body: { sku, title, author, price, category, description, active }
 */
router.post('/books', authenticateToken, requireAdmin, async (req, res, next) => {
  try {
    const { sku, title, author, price, category, description, active } = req.body;

    // SKU is optional - will be auto-generated if not provided
    if (!title || !author || !price || !category) {
      return res.status(400).json({
        error: 'Validation error',
        message: 'Required fields: title, author, price, category'
      });
    }

    const bookRequest = {
      book: {
        sku: sku || '', // Optional SKU
        title,
        author,
        price: {
          amount: Math.round(parseFloat(price) * 100), // Convert to cents
          currency: 'USD'
        },
        category,
        description: description || '',
        active: active !== undefined ? active : true
      }
    };

    const response = await grpcClient.call('catalog', 'CreateBook', bookRequest);

    const book = {
      sku: response.book.sku,
      title: response.book.title,
      author: response.book.author,
      price: response.book.price ? {
        amount: response.book.price.amount / 100,
        currency: response.book.price.currency
      } : null,
      category: response.book.category,
      description: response.book.description,
      active: response.book.active,
      created_at: response.book.created_at,
      updated_at: response.book.updated_at
    };

    res.status(201).json({
      message: 'Book created successfully',
      book
    });
  } catch (error) {
    next(error);
  }
});

/**
 * PUT /api/catalog/books/:sku
 * Update an existing book (Admin only)
 * Body: { title, author, price, category, description, active }
 */
router.put('/books/:sku', authenticateToken, requireAdmin, async (req, res, next) => {
  try {
    const { sku } = req.params;
    const { title, author, price, category, description, active } = req.body;

    const bookUpdate = {
      book: {
        sku
      },
      update_mask: []
    };

    if (title !== undefined) {
      bookUpdate.book.title = title;
      bookUpdate.update_mask.push('title');
    }
    if (author !== undefined) {
      bookUpdate.book.author = author;
      bookUpdate.update_mask.push('author');
    }
    if (price !== undefined) {
      bookUpdate.book.price = {
        amount: Math.round(parseFloat(price) * 100),
        currency: 'USD'
      };
      bookUpdate.update_mask.push('price');
    }
    if (category !== undefined) {
      bookUpdate.book.category = category;
      bookUpdate.update_mask.push('category');
    }
    if (description !== undefined) {
      bookUpdate.book.description = description;
      bookUpdate.update_mask.push('description');
    }
    if (active !== undefined) {
      bookUpdate.book.active = active;
      bookUpdate.update_mask.push('active');
    }

    if (bookUpdate.update_mask.length === 0) {
      return res.status(400).json({
        error: 'Validation error',
        message: 'At least one field must be provided for update'
      });
    }

    const response = await grpcClient.call('catalog', 'UpdateBook', bookUpdate);

    const book = {
      sku: response.book.sku,
      title: response.book.title,
      author: response.book.author,
      price: response.book.price ? {
        amount: response.book.price.amount / 100,
        currency: response.book.price.currency
      } : null,
      category: response.book.category,
      description: response.book.description,
      active: response.book.active,
      created_at: response.book.created_at,
      updated_at: response.book.updated_at
    };

    res.json({
      message: 'Book updated successfully',
      book
    });
  } catch (error) {
    next(error);
  }
});

module.exports = router;

