import simplejson, os.path, sys

from django.conf import settings

from molly.conf import all_apps, app_by_local_name, app_by_application_name
from molly.batch_processing.models import Batch
from molly.utils.misc import get_norm_sys_path

def load_batches():
    batch_details = []
    for app in all_apps():
        for provider in app.providers:
            for method_name in dir(provider):
                method = getattr(provider, method_name)
                if not getattr(method, 'is_batch', False):
                    continue
                    
                batch_details.append({
                    'title': method.__doc__ or provider.class_path,
                    'local_name': app.local_name,
                    'provider_name': provider.class_path,
                    'method_name': method_name,
                    'cron_stmt': method.cron_stmt,
                    'initial_metadata': method.initial_metadata,
                })

    batches = set()
    for batch_detail in batch_details:
        batch, _ = Batch.objects.get_or_create(
            local_name = batch_detail['local_name'],
            provider_name = batch_detail['provider_name'],
            method_name = batch_detail['method_name'],
            defaults = {'title': batch_detail['title'],
                        'cron_stmt': batch_detail['cron_stmt'],
                        '_metadata': simplejson.dumps(batch_detail['initial_metadata'])})
        batches.add(batch)
    for batch in Batch.objects.all():
        if not batch in batches:
            batch.delete()

def run_batch(local_name, provider_name, method_name):
    # This will force the loading of the molly.utils app, attaching its log
    # handler lest the batch logs anything that needs e-mailing.
    app_by_application_name('molly.utils')
    
    batch = Batch.objects.get(
        local_name=local_name,
        provider_name=provider_name,
        method_name=method_name)

    batch.run(True)

    return batch.log

def _escape(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')

def create_crontab(filename):
    load_batches()

    sys_path = get_norm_sys_path()

    f = open(filename, 'w') if isinstance(filename, basestring) else filename
    f.write("# Generated by Molly. Do not edit by hand, or else your changes\n")
    f.write("# will be overwritten.\n\n")
    f.write('MAILTO="%s"\n' % ','.join(l[1] for l in settings.ADMINS))
    f.write("DJANGO_SETTINGS_MODULE=%s\n" % os.environ['DJANGO_SETTINGS_MODULE'])
    f.write("PYTHONPATH=%s\n\n" % ':'.join(sys_path))

    for batch in Batch.objects.all():
        if not batch.enabled:
            continue
        f.write('%s %s %s "%s" "%s" "%s"\n' % (
            batch.cron_stmt.ljust(20),
            sys.executable,
            os.path.abspath(os.path.join(os.path.dirname(__file__), 'scripts', 'run_batch.py')),
            _escape(batch.local_name),
            _escape(batch.provider_name),
            _escape(batch.method_name),
        ))