# La Tournée - Dispatch Order Exercise

To run the app, just run:
```
docker-compose -f docker-compose.yml up
```
You can explore the API at http://localhost:8888/.
(on the first build, the migration can be launched before 
the SQL server is ready so you'd need to relaunch the 
command if this happens -- yeah that's not ideal, sorry for
that).

It will spin up server, database and test database.

To run the tests, when the above server is running:
```
docker exec -it la_tournee_web_1 pytest
```
(you may have to rename `la_tournee_web_1` accordingly to the
actual name of the `web` container).


To format and sort imports:
```
docker exec -it la_tournee_web_1 black .
docker exec -it la_tournee_web_1 isort .
```

## Interesting files

### [`app/tests/test_orders.py`](app/tests/test_orders.py)

The tests are decoupled into 2 functions:
* the first one just ensure the received JSON is well 
  processed by the API is well understood.
* the second ensure the complicated logic behaves well

### [`app/models.py`](app/models.py)

The product table structure is slightly different from the
json we have in the example.

Indeed, to compute the order dispatch, we only need to
know if we can use supplier crates and in this case
how many slots there are in those crates. That's why
`packing` is an optional integer.

We also need to know the size of the product. The deposit price 
should be derived from this size (and will probably change
over time), on the contrary of what is suggested in the
store JSON. By the way, it would be safer expressing this
price in cents in order to only compute with integer,
since floating point arithmetic can be problematic for
price computations.


The `load_product_from_json` is called at server startup,
it would be maybe better having some command to launch
this but I didn't have time to search how to do this
properly with FastAPI.


### [`app/api/endpoints/orders.py`](app/api/endpoints/orders.py)

The main role of this endpoint is to ensure the requested
products exist and joining them with the Product table
to have the packing and the size of each item.

Once we have clean data, we can go through...

### [`app/core/dispatch.py`](app/core/dispatch.py)

This is the file encapsulating the complicated logic to dispatch the order. The main function is 
`to_dispatch_response` which is a "pure" function 
meaning we ca easily test it.

## Dev container

I tried to develop in VSCode dev container, the
configuration is in the `.devcontainer` folder.

This enables VSCode using the container which is used
to run the server, hence Pylance knows the libraries
used.

The experience was not entirely satisfactory: the startup
time is consequent and some features work randomly 
(e.g. "formatting on save" doesn't always work...).


## If I had more time

* Check types with MyPy
* Automating testing/formating before launching in production
  (probably in the CI)
* Write more tests for the dispatch logic, maybe some fuzzy
  tests checking we can always at least fit the products
  in the crates (maybe complicated?)
* Improve the dispatch algorithm (the tests have a sub 
  optimal case).
* Writing a separated docker architecture for production:
  the DB will probably be a managed one in AWS or so, thus
  we don't need this in the docker-compose.

