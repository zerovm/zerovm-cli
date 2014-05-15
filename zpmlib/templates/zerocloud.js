//  Copyright 2014 Rackspace, Inc.
//
//  Licensed under the Apache License, Version 2.0 (the "License");
//  you may not use this file except in compliance with the License.
//  You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
//  Unless required by applicable law or agreed to in writing,
//  software distributed under the License is distributed on an "AS
//  IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
//  express or implied. See the License for the specific language
//  governing permissions and limitations under the License.

/*
 *  ZeroVM on Swift (ZeroCloud) client.
 */
function ZeroCloudClient() {
    this._token = null;
}

/*
 * Authenticate to Keystone. Call this before calling other methods
 * that talk with Swift.
 *
 * If Keystone and Swift are served from differnet domains, you must
 * install a CORS (Cross-Origin Resource Sharing) middleware in Swift.
 * Otherwise the authentication requests made by this function wont be
 * allowed by the browser.
 */
ZeroCloudClient.prototype.auth = function (opts, success) {
    var defaults = {'version': '2.0', 'success': $.noop};
    var args = {'success': success};
    var merged = $.extend(defaults, opts, args);
    switch (merged.version) {
    case '0.0':
        this._auth0(merged);
        break;
    case '1.0':
        this._auth1(merged);
        break;
    default:
        this._auth2(merged);
        break;
    }
}

/*
 * No authentication. This is used when no authentication is
 * necessary.
 *
 * The opts argument is a plain object with these keys:
 *
 * - swiftUrl
 */
ZeroCloudClient.prototype._auth0 = function (opts) {
    this._swiftUrl = opts.swiftUrl;
    opts.success();
}

/*
 * Swift v1 authentication.
 *
 * The opts argument is a plain object with these keys:
 *
 * - authURL
 * - username
 * - password
 */
ZeroCloudClient.prototype._auth1 = function (opts) {
    var self = this;
    $.ajax({
        'type': 'GET',
        'url': opts.authUrl,
        'cache': false,
        'headers': {
            'X-Auth-User': opts.username,
            'X-Auth-Key': opts.password
        },
        'success': function (data, status, xhr) {
            self._token = xhr.getResponseHeader('X-Auth-Token');
            self._swiftUrl = xhr.getResponseHeader('X-Storage-Url');
            opts.success();
        }
    });
}

/*
 * Swift v2 authentication. This will login to Keystone and obtain an
 * authentication token.
 *
 * The opts argument is a plain object with these keys:
 *
 * - authURL
 * - username
 * - password
 * - tenant
 */
ZeroCloudClient.prototype._auth2 = function (opts) {
    var headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json'};
    var payload = {'auth':
                   {'tenantName': opts.tenant,
                    'passwordCredentials':
                    {'username': opts.username,
                     'password': opts.password}}};
    var self = this;
    $.ajax({
        'type': 'POST',
        'url': opts.authUrl + '/tokens',
        'data': JSON.stringify(payload),
        'cache': false,
        'success': function (data) {
            self._token = data.access.token.id;
            $.each(data.access.serviceCatalog, function (i, service) {
                if (service.name == 'swift') {
                    self._swiftUrl = service.endpoints[0].publicURL;
                    return false;  // break for-each loop
                }
            });
            opts.success();
        },
        'dataType': 'json',
        'contentType': 'application/json',
        'accepts': 'application/json'
    });
};

/*
 * Execute a job. The job description will be serialized as JSON and
 * sent to Swift. The "stdout" from the job, if any, will be passed to
 * the success callback function.
 */
ZeroCloudClient.prototype.execute = function (job, success) {
    var headers = {'X-Zerovm-Execute': '1.0'};
    if (this._token) {
        headers['X-Auth-Token'] = this._token;
    }
    $.ajax({
        'type': 'POST',
        'url': this._swiftUrl,
        'data': JSON.stringify(job),
        'headers': headers,
        'cache': false,
        'success': (success || $.noop),
        'contentType': 'application/json',
    });
};

/*
 * Compute a Swift URL. This is a URL of the form
 * swift://<user>/<relativePath>.
 */
ZeroCloudClient.prototype.swiftPath = function (relativePath) {
    var user = this._swiftUrl.slice(this._swiftUrl.lastIndexOf('/') + 1);
    return 'swift://' + user + '/' + relativePath;
}

/*
 * Escape command line argument. Command line arguments in a job
 * description should be separated with spaces after being escaped
 * with this function.
 */
function escapeArg (value) {
    function hexencode (match) {
        return "\\x" + match.charCodeAt(0).toString(16)
    }
    return value.replace(/[\\", \n]/g, hexencode)
}
