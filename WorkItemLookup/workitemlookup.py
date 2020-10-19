# Keypirinha: a fast launcher for Windows (keypirinha.com)

import keypirinha as kp
import keypirinha_util as kpu
#import re

class WorkItemLookup(kp.Plugin):
    """Open work item URL from ID"""

    CONFIG_SECTION_MAIN = "main"
    CONFIG_SECTION_SITE = "site"

    DEFAULT_URL_PATTERN = ""
    DEFAULT_ITEM_LABEL_FORMAT = "WorkItem Site {site_name}"
    DEFAULT_HISTORY_KEEP = kp.ItemHitHint.NOARGS

    ITEM_LABEL_PREFIX = "Workitem: "

    url_pattern = ""
    sites = {}

    _debug = True

    def __init__(self):
        super().__init__()

    def on_start(self):
        pass

    def on_catalog(self):
        self._read_config()
        catalog = []
        for site_name, site in self.sites.items():
            catalog.append(self.create_item(
                category=kp.ItemCategory.REFERENCE,
                label=site['item_label'],
                short_desc=" {}".format(site['label']),
                target=kpu.kwargs_encode(site=site_name),
                args_hint=kp.ItemArgsHint.ACCEPTED,
                hit_hint=self.DEFAULT_HISTORY_KEEP))
        self.set_catalog(catalog)

    def on_suggest(self, user_input, items_chain):
        if items_chain and items_chain[-1].category() == kp.ItemCategory.REFERENCE:
            clone = items_chain[-1].clone()
            clone.set_args(user_input.strip())
            self.set_suggestions([clone])

    def on_execute(self, item, action):
        if item.category() != kp.ItemCategory.REFERENCE:
            return

        try:
            item_target = kpu.kwargs_decode(item.target())
            site_name = item_target['site']
        except Exception as exc:
            self.dbg(str(exc))
            return

        if site_name not in self.sites:
            self.warn('Could not execute item "{}". Site "{}" not found.'.format(item.label(), site_name))
            return

        site = self.sites[site_name]

        if len(item.raw_args()) > 0:
            itemId = item.raw_args()
            final_url = site['url'].format(itemId=itemId)
            kpu.web_browser_command(
                url=final_url, execute=True)

    def on_suggest_x(self, user_input, items_chain):
        if not self.url_pattern:
            return

        itemId = user_input.strip()
        url = self.url_pattern.format(itemId=itemId)

        hit_hint = kp.ItemHitHint.IGNORE
        suggestions = [self.create_item(
            category=kp.ItemCategory.URL,
            label=f"ID: {user_input}",
            short_desc="", #f"Open work item URL for #: {user_input}",
            target=url,
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.IGNORE)]

        self.set_suggestions(suggestions)
        return

    def on_execute_x(self, item, action):
        kpu.execute_default_action(self, item, action)
        #kpu.shell_execute(item.target())

    def on_events(self, flags):
        if flags & kp.Events.PACKCONFIG:
            self.info("Configuration changed, rebuilding catalog...")
            self.on_catalog()

    def _read_config(self):
        self.sites = {}

        settings = self.load_settings()
        self.url_pattern = settings.get_stripped(
            "url", self.CONFIG_SECTION_MAIN, self.DEFAULT_URL_PATTERN)

        self.dbg("work item url pattern: " + self.url_pattern)

        item_label_format = settings.get_stripped(
            "item_label_format",
            section=self.CONFIG_SECTION_MAIN,
            fallback=self.DEFAULT_ITEM_LABEL_FORMAT)

        # read "site" sections
        for section in settings.sections():
            if section.lower().startswith(self.CONFIG_SECTION_SITE + "/"):
                site_label = section[len(self.CONFIG_SECTION_SITE) + 1:].strip()
            else:
                continue

            if not len(site_label):
                self.warn('Ignoring empty site name (section "{}").'.format(section))
                continue

            forbidden_chars = (':;,/|\\')
            if any(c in forbidden_chars for c in site_label):
                self.warn(
                    'Forbidden character(s) found in site name "{}". Forbidden characters list "{}"'
                    .format(site_label, forbidden_chars))
                continue

            if site_label.lower() in self.sites.keys():
                self.warn('Ignoring duplicated site "{}" defined in section "{}".'.format(site_label, section))
                continue

            site_item_label = item_label_format.format(
                site_name=site_label, plugin_name=self.friendly_name())

            site_url = settings.get_stripped("url", section=section)
            if not len(site_url):
                self.warn('Ignoring site "{}" defined in section "{}" with emtpy "url".'.format(site_label, section))
                continue

            if '{itemId}' not in site_url:
                self.warn('Search-terms placeholder "{{itemId}}" not found in URL of site "{}". Site ignored.'.format(site_label))
                continue

            self.sites[site_label.lower()] = {
                'label': site_label,
                'url': site_url,
                'item_label': site_item_label
            }

            self.dbg(self.sites[site_label.lower()])
