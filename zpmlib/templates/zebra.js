function ZwiftClient(authUrl, tenant, username, password) {
    this._authUrl = authUrl;
    this._tenant = tenant;
    this._username = username;
    this._password = password;

    this._token = null;
    this._swiftUrl = null;
}

ZwiftClient.prototype.auth = function (success) {
    var headers = {'Content-Type': 'application/json',
                   'Accept': 'application/json'};
    var payload = {'auth':
                   {'tenantName': this._tenant,
                    'passwordCredentials':
                    {'username': this._username,
                     'password': this._password}}};
    var self = this;
    $.ajax({
        'type': 'POST',
        'url': this._authUrl,
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
            (success || $.noop)();
        },
        'dataType': 'json',
        'contentType': 'application/json',
        'accepts': 'application/json'
    });
};

ZwiftClient.prototype.execute = function (job, success) {
    var headers = {'X-Auth-Token': this._token,
                   'X-Zerovm-Execute': '1.0'}
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

function escapeArg (value) {
    function hexencode (match) {
        return "\\x" + match.charCodeAt(0).toString(16)
    }
    return value.replace(/[\\", \n]/g, hexencode)
}
