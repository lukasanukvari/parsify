# Parsify

Stop writing multiple parser scripts for parsing different websites.
With __Parsify__ you can have a single few lines script and the configuration file to fit your parser to different websites.

## Contents
* [Installation](#installation)
* [Usage](#usage)
* [Handbook Tutorial](#handbook-Tutorial)
  * [Required Fields](#required-fields)
  * [Advanced Fields](#advanced-fields)
  * [Simple Example](#simple-example)
  * [Advanced Example](#advanced-example)
* [Contact](#contact)
* [License](#license)
* [Contributing](#contributing)

## Installation
`pip install parsify`

## Usage
Make sure you have your configuration file (usually `handbook.json`) ready.

```python
import parsify as pf


# Create Parsify engine
ngn = pf.Engine(handbook='handbook.json')

# Run a single step
# Provide step name as an argument
# Should be in Engine.current_parser
# Should not have any "dynamic_variables" when custom using this method
# By default Engine.current_parser is the first parser in the Handbook
step_result = ngn.stepshot(step='get_products')
# print(step_result)

# Parse a single website (must be configured in "handbook.json")
# Provide scope name as an argument
scope_result = ngn.scopeshot(parser='example.com')
# print(scope_result)

# Run all the parsers that are configured in "handbook.json"
final_result = ngn.parse()
# print(final_result)
```

## Handbook Tutorial

### Required Fields
* __Handbook__ file should start with ___"parser"___ key value of which is the array of parsers.
* Each parser in the array should have two keys:
  * ___"scope"___ - String: Name of the parser. Usually website name, i.e. _"example.com"_.
  * ___"steps"___ - Array: Steps to parse.
* Each step should have at least following fields:
  * ___"name"___ - String: Unique name of the step. This field will make possible to access this step's results and dynamic variables in the proceeding steps (if needed).
  * ___"chain_id"___ - Integer: Steps with the same chain id will be executed as a sequence of steps on every iteration.
  * ___"url"___ - String: Target url of the request(s) for the current step.
  * ___"method"___ - String: Request method for the current step.
  * ___"output_path"___ String: Path of the result data in response. Use dots if it's multi-nested, for example, if needed result is in ___response -> "data" -> "products"___, __"output_path"__ should be ___"data.products"___.
  * ___"output"___ Dictionary: 

## License
Distributed under the MIT License. See [`LICENSE`](./LICENSE) file for more information.

## Contact
Luka Sosiashvili - [@lukasanukvari](https://twitter.com/lukasanukvari) - luksosiashvili@gmail.com

Project Link: [https://github.com/lukasanukvari/parsify](https://github.com/lukasanukvari/parsify)

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.