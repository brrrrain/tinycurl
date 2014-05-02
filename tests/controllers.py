import time
import bottle

@bottle.route('/hammer_mode/<fail_attempts>/<clear>')
def hammer_mode(fail_attempts=2, clear=0):
    hammer_file = '/tmp/hammer_counter'

    if int(clear) > 0:
        with open(hammer_file, 'w') as f:
            f.write('0')
        return ""

    with open(hammer_file) as f:
        attempts = int(f.read())

    if attempts < int(fail_attempts):
        with open(hammer_file, 'w') as f:
            f.write(str(attempts+1))
        time.sleep(10)
        #return ""
    else:
        return "test"

@bottle.route('/looping')
def looping():
    bottle.redirect('/looping')

@bottle.route('/test')
def test():
    return "test_simple_load"

@bottle.route('/redir')
def redir():
    bottle.redirect('/redirect_destination')

@bottle.route('/redirect_destination')
def redir_destination():
    return "redirect"

@bottle.post('/simple_post')
def simple_post():
    return bottle.request.POST.get('some_input', '')

@bottle.route('/cookies')
def simple_cookies():
    bottle.response.set_cookie('test_cookie', 'test')

@bottle.route('/set_get_cookies')
def set_get_cookies():
    cookie = bottle.request.get_cookie('test_cookie', '')

    if cookie:
        return cookie
    else:
        bottle.response.set_cookie('test_cookie', 'test')

@bottle.route('/header')
@bottle.post('/header')
def header():
    return bottle.request.get_header('Test-header', 'None')

@bottle.route('/redirect_to_header')
@bottle.post('/redirect_to_header')
def redirect_to_header():
    bottle.redirect('/header')

@bottle.route('/redirect_to_useragent')
@bottle.post('/redirect_to_useragent')
def redirect_to_useragent():
    bottle.redirect('/useragent')

@bottle.route('/useragent')
@bottle.post('/useragent')
def useragent():
    return bottle.request.get_header('User-agent', 'None')

@bottle.route('/referer')
@bottle.post('/referer')
def referer():
    return bottle.request.get_header('Referer', 'None')
