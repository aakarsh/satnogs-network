#!/usr/bin/env python
#
# Script to postprocess OpenAPI generated schema
#
# Copyright (C) 2020 Libre Space Foundation <https://libre.space/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import sys

import yaml


class Dumper(yaml.Dumper):
    def ignore_aliases(self, data):
        return True


parser = argparse.ArgumentParser(description="Postprocess OpenAPI generated schema")
parser.add_argument('--api-version', type=str, help='Set API version')
parser.add_argument('--server-url', type=str, help='Set API server base URL')
parser.add_argument('--expand-aliases', action='store_true', help='Expand anchors and aliases')
parser.add_argument(
    '--enable-apikey-auth', action='store_true', help='Enable DRF API key authentication'
)
parser.add_argument(
    'input_file',
    type=argparse.FileType('r', encoding='UTF-8'),
    help='OpenAPI schema file or \'-\' for stdin'
)
args = parser.parse_args()

schema = yaml.safe_load(args.input_file)
if args.api_version is not None:
    schema['info']['version'] = args.api_version

if args.server_url is not None:
    schema['servers'] = [{'url': args.server_url}]

if args.enable_apikey_auth:
    schema.update(
        {
            'components': {
                'securitySchemes': {
                    'ApiKeyAuth': {
                        'type': 'apiKey',
                        'in': 'header',
                        'name': 'Authorization'
                    }
                }
            },
            'security': [
                {
                    'ApiKeyAuth': []
                },
            ]
        }
    )

if args.expand_aliases:
    schema_dump = yaml.dump(
        schema, default_flow_style=False, sort_keys=False, Dumper=Dumper
    ).encode('utf-8')
else:
    schema_dump = yaml.dump(schema, default_flow_style=False, sort_keys=False).encode('utf-8')

sys.stdout.buffer.write(schema_dump)
