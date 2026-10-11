"""Per-app cutout and placement settings. Apps without an entry use App() (or GOOGLE for data/google)."""

from dataclasses import replace

from .unify import App

# data/google holds Google's redesigned icons on white
GOOGLE = App(key='outside', bg=(255, 255, 255), recolor=None, frac=0.72)

OVERRIDES: dict[str, App] = {
    'app.revanced.manager.flutter': App(frac=0.60),
    'com.bhxhapp': App(frac=0.715),
    'com.brave.browser': App(recolor=None),
    'com.cloudflare.cloudflareoneagent': App(key='warm', recolor=None),
    'com.coinmarketcap.android': App(key='white', recolor=(56, 97, 251)),
    'com.exteragram.messenger': App(
        key='white', wlo=80, whi=190, recolor=(245, 65, 66), frac=0.48, dx=-0.022, dy=0.025
    ),
    'com.facebook.orca': App(key='outside', recolor=None),
    'com.finx.vikki': App(recolor=None, frac=0.86, specks=False),
    'com.google.android.apps.docs': replace(GOOGLE, holes=True),
    'com.google.android.apps.maps': replace(GOOGLE, holes=True),
    'com.gsm.customer': App(recolor=None),
    'com.hihonor.appmarket': App(key='white', recolor=(70, 150, 255), frac=0.74),
    'com.hihonor.ouc': App(key='whitefill', recolor=None, frac=0.62),
    'com.hihonor.search': App(key='white', recolor=(30, 140, 255), frac=0.64),
    'com.inbody2014.inbody': App(recolor=(235, 45, 55)),
    'com.instagram.android': App(key='white', recolor='field'),
    'com.mbmobile': App(recolor=None),
    'com.msb.digibank.retail': App(recolor=None),
    'com.mservice.momotransfer': App(key='white', recolor=(235, 40, 150), frac=0.62),
    'com.okinc.okex.gp': App(key='white', recolor=None, frac=0.56),
    'com.ots.c08.vnetraffic': App(recolor=None, frac=0.72, dy=0.03),
    'com.readdle.spark': App(key='white', recolor='field'),
    'com.reddit.frontpage': App(key='checker', recolor=None),
    'com.truecaller': App(recolor=None),
    'com.vietnamairlines.android.app': App(key='sat', recolor=None),
    'com.vnid': App(recolor=None, frac=0.74, dy=-0.02),
    'com.vnp.myvinaphone': App(key='white', recolor=(30, 120, 255)),
    'com.x8bit.bitwarden': App(key='white', recolor=(23, 93, 220)),
    'com.zing.zalo': App(recolor=None, frac=0.8925, dx=0.0525, dy=-0.0569),
    'de.mobileconcepts.cyberghost': App(recolor=None),
    'dev.anilbeesetti.nextplayer': App(recolor=None, frac=0.46, dx=0.045),
    'dev.imranr.obtainium': App(recolor=None),
    'hk.easyvan.app.client': App(key='white', recolor=(241, 102, 34), crop=(0, 0, 1, 0.72)),
    'io.ente.auth': App(recolor=None),
    'io.netbird.client': App(recolor=None),
    'mega.privacy.android.app': App(key='white', recolor=(217, 39, 46)),
    'moe.shizuku.privileged.api': App(recolor=None),
    'vn.android.consumer.sgc': App(recolor=(40, 90, 255)),
    'vn.com.encapital.arrow': App(key='white', recolor=(230, 40, 40)),
    'vn.com.vng.zalopay': App(recolor=None, lift=True),
    'xyz.be.customer': App(recolor=None),
}
