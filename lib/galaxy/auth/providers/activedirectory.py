"""
Created on 15/07/2014

@author: Andrew Robinson
"""

from galaxy.exceptions import ConfigurationError
from ..providers import AuthProvider

import logging
log = logging.getLogger(__name__)


def _get_subs(d, k, params):
    if k not in d:
        raise ConfigurationError("Missing '%s' parameter in Active Directory options" % k)
    return str(d[k]).format(**params)


class ActiveDirectory(AuthProvider):
    """
    Attempts to authenticate users against an Active Directory server.

    If options include search-fields then it will attempt to search the AD for
    those fields first.  After that it will bind to the AD with the username
    (formatted as specified).
    """
    plugin_type = 'activedirectory'

    def authenticate(self, username, password, options):
        """
        See abstract method documentation.
        """
        log.debug("Username: %s" % username)
        log.debug("Options: %s" % options)

        failure_mode = False  # reject but continue
        if options.get('continue-on-failure', 'False') == 'False':
            failure_mode = None  # reject and do not continue

        try:
            import ldap
        except:
            log.debug("User: %s, ACTIVEDIRECTORY: False (no ldap)" % (username))
            return (failure_mode, '')

        # do AD search (if required)
        params = {'username': username, 'password': password}
        if 'search-fields' in options:
            try:
                # setup connection
                ldap.set_option(ldap.OPT_REFERRALS, 0)
                l = ldap.initialize(_get_subs(options, 'server', params))
                l.protocol_version = 3

                if 'search-user' in options:
                    l.simple_bind_s(_get_subs(options, 'search-user', params), _get_subs(options, 'search-password', params))
                else:
                    l.simple_bind_s()

                scope = ldap.SCOPE_SUBTREE

                # setup search
                attributes = [_.strip().format(**params) for _ in options['search-fields'].split(',')]
                result = l.search(_get_subs(options, 'search-base', params), scope, _get_subs(options, 'search-filter', params), attributes)

                # parse results
                _, suser = l.result(result, 60)
                dn, attrs = suser[0]
                log.debug(("AD dn: %s" % dn))
                log.debug(("AD Search attributes: %s" % attrs))
                if hasattr(attrs, 'has_key'):
                    for attr in attributes:
                        if attr in attrs:
                            params[attr] = str(attrs[attr][0])
                        else:
                            params[attr] = ""
                params['dn'] = dn
            except Exception:
                log.exception('ACTIVEDIRECTORY Search Exception for User: %s' % username)
                return (failure_mode, '')
        # end search

        # bind as user to check their credentials
        try:
            # setup connection
            ldap.set_option(ldap.OPT_REFERRALS, 0)
            l = ldap.initialize(_get_subs(options, 'server', params))
            l.protocol_version = 3
            l.simple_bind_s(_get_subs(options, 'bind-user', params), _get_subs(options, 'bind-password', params))
        except Exception:
            log.exception('ACTIVEDIRECTORY Authenticate Exception for User %s' % username)
            return (failure_mode, '')

        log.debug("User: %s, ACTIVEDIRECTORY: True" % (username))
        return (True, _get_subs(options, 'auto-register-username', params))

    def authenticate_user(self, user, password, options):
        """
        See abstract method documentation.
        """
        return self.authenticate(user.email, password, options)[0]


__all__ = ['ActiveDirectory']
