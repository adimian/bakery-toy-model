# bakery-toy-model
A toy infrastructure for an imaginary bakery company. Used to build integrations in kirby.

# Requirements

- redis server >= 5.0.4

# Installing

```bash
pip install -e git+https://github.com/adimian/bakery-toy-model.git#egg=bakery 
```

# Running

By default it will serve from `127.0.0.1` on port `8000`

## Easy mode

```bash
bakery serve
```

## Troll mode

```bash
TROLL=yes bakery serve
```

## Change port (e.g. to 5001)

```bash
bakery serve -p 5001
```


## Running more workers (e.g. 4)

```bash
bakery serve -w 4
```

# Services

You can find the swagger for the services at the root `/`

# Admin interface

You can find the admin interface at `/admin`