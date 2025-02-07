# build html5 , bootstrap based page to format and query json

JSONPath queries example  with sample JSON data:

```json
{
  "store": {
    "books": [
      {
        "title": "Book 1",
        "price": 10.95,
        "authors": ["John", "Jane"]
      },
      {
        "title": "Book 2",
        "price": 22.99,
        "authors": ["Bob"]
      }
    ],
    "bicycles": [
      {
        "color": "red",
        "price": 399.99
      }
    ]
  }
}
```

Queries:
- `$.store.books[*].title` - Get all book titles
- `$.store.books[?(@.price < 20)].title` - Get titles of books under $20
- `$.store.books[*].authors[*]` - Get all authors
- `$.store..price` - Get all prices from any object
- `$.store.books[0]` - Get first book's details