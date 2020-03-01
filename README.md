# WSGI Transponder 

It is a glue between a wsgi server and anything than can serve http 1.0/1.1 protocol.
Why "transponder"? 

That's because it repacks requests HTTP headers and content within the WSGI application script before transmitting it to the worker web application. Then, it unpacks headers and content and emits them to the WSGI server. 

It is pretty like a proxy, but with operations that may alter the original request, such as headers'orders.

It should work well with non-blocking web applications.

## Motivation

My hoster already supports WSGI applications, therefore, it just needs a glue to support a PSGI application, and the transponder stands as this glue.
More on [this blog post](https://ngs.ma/index.php/2020/03/01/deploy-mojolicious-app-on-shared-hosting/)

## Prerequisites

* A WSGI web server such as `waitress`, `uWSGI`, `Phusion Passenger`
* Python 2.7.15 or newer (not tested with Python 3)

## Installation

1. Create a WSGI application on a hoster that supports this technology
2. Download or upload `wsgi_transponder.py` in your webapp root folder
```bash
curl -O https://raw.githubusercontent.com/xlat/wsgi-transponder/master/wsgi_transponder.py
```
3. Point your WSGI application to `wsgi_transponder.py`
4. Create and edit a `transponder.config.json` file in webapp root folder
```bash
curl -O https://raw.githubusercontent.com/xlat/wsgi-transponder/master/transponder.config.json
```
5. Set WSGI entry point to: `application`
6. Start the WSGI web application
7. Point to your app in the browser

## Configuration 

The configuration file must be named `transponder.config.json` and be in the same folder than `wsgi_transponder.py`, and be a valid JSON file with the following structure:
```JSON	
	{
		"profiles": {
			"hypnotoad": {
				"arguments": [
					"~/mojowebapp/local/bin/hypnotoad -f app-light.pl"
				],
				"host": "localhost",
				"port": 8080,
				"force-accept-encoding": true,
				"accept-encoding": "gzip, deflate, br",
				"shell": true,
				"debug": false,
				"trace": "transponder.log"
			},
			"plackup": {
				"arguments": "..."
			},
			"mojo-daemon": {
				"arguments": "..."
			},
			"something-else": {
				"arguments": "..."
			}			
		},
		"default": "hypnotoad"
	}
```	

### profiles (object)

The `profiles` key is the place where you will define your application profiles.
A profile consists of sub keys described below:

#### arguments (array or string)

The `arguments` key defines the command line that will be invoked to start your application worker. It uses [subprocess.Popen](https://docs.python.org/2/library/subprocess.html#subprocess.Popen).
* You can define `arguments` as an array:
```JSON
		"arguments": [ "/bin/perl", "mywebapp.pl", "daemon", "-l", "http://*:5000" ],
```
* Or as a string describing the whole command:
```JSON
		"arguments": "perl.exe mywebapp.pl daemon -l http://*:5000",
```

#### shell (boolean)

This parameter let's change the [subprocess.Popen](https://docs.python.org/2/library/subprocess.html#subprocess.Popen) shell argument, it's value may depend on your needs/platform.

#### host (string)

The `host` parameter define the host where your worker is listening, generaly `localhost`.

#### port (number)

The `port` parameter is the port number where your worker is listening.

#### force-accept-encoding (boolean)

The `force-accept-encoding` parameter is a workaround for application servers that strip `Accept-Encoding` HTTP header, such as `Phusion Passenger`.

#### accept-encoding (string)

The `accept-encoding` parameter is to be used aside the `force-accept-encoding` parameter, it is useful to allow gzip compression within your worker.

#### trace (filename)

The `trace` parameter defines the filename to trace logs from the transponder.

#### debug (boolean)

The `debug` parameter, when set to `true` makes transponder to trace more things in the trace file.

### default (string)

The `default` key defines the default profile to use.
To override configuration default profile, use the `WSGIT_PROFILE` environment variable:
```bash
export WSGIT_PROFILE=plackup
```
On most hosters you define environment variables directly in the WSGI application settings.

## Contributing

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D

## Bugs

* Some WSGI servers may drop "Accept-Enconding" header, disabling defacto gzip compression (workaround: see configuration)
* may be a lot more, only GET and POST http verbs have been tested, so feel free to [open an issue](https://github.com/xlat/wsgi-transponder/issues)
	
## Limitations

* Does not support websocket: WSGI specifications does not allow hop-to-hop HTTP Feature.
  see: https://www.python.org/dev/peps/pep-0333/#other-http-features

## Author

* **Nicolas Georges** - *Initial work* - [ngs.ma](https://ngs.ma)

## License
	
This project is licensed under the Artistic License 2.0 - See https://opensource.org/licenses/artistic-license-2.0
