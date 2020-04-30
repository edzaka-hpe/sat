"""
Functions for obtaining version information about docker containers/images.

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import docker


def get_dockers():
    """Return names and version info from installed images.

    Returns:
        A list of lists; each containing 3+ entries. The first entry contains
        the docker image id. The second contains the image's base-name. The
        third on to the end contain the image's versions.
    """

    client = docker.from_env()

    ret = []
    for image in client.images.list():
        tags = image.tags
        if len(tags) > 0:

            # Docker id is returned like 'sha256:fffffff'
            full_id = image.id.split(':')[-1]
            short_id = image.short_id.split(':')[-1]
            fields = tags[0].split(':')
            name = fields[-2].split('/')[-1]

            versions = []
            for tag in tags:
                version = tag.split(':')[-1]
                if version not in versions and version != 'latest':
                    versions.append(version)

            if not versions:
                versions.append('latest')

            ret.append([name, short_id, ', '.join(versions)])

    ret.sort()
    return ret
