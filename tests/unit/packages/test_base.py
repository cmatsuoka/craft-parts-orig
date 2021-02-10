# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2017-2021 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import textwrap

from craft_parts.packages._base import BaseRepository


class TestFixPkgConfig:
    """Check the normalization of pkg-config files."""

    def test_fix_pkg_config(self, tmpdir):
        pc_file = tmpdir / "granite.pc"

        pc_file.write_text(
            textwrap.dedent(
                """\
                prefix=/usr
                exec_prefix=${prefix}
                libdir=${prefix}/lib
                includedir=${prefix}/include

                Name: granite
                Description: elementary\'s Application Framework
                Version: 0.4
                Libs: -L${libdir} -lgranite
                Cflags: -I${includedir}/granite
                Requires: cairo gee-0.8 glib-2.0 gio-unix-2.0 gobject-2.0
                """
            ),
            encoding=None,
        )

        BaseRepository.normalize(tmpdir)

        expected_pc_file_content = textwrap.dedent(
            f"""\
            prefix={tmpdir}/usr
            exec_prefix=${{prefix}}
            libdir=${{prefix}}/lib
            includedir=${{prefix}}/include

            Name: granite
            Description: elementary's Application Framework
            Version: 0.4
            Libs: -L${{libdir}} -lgranite
            Cflags: -I${{includedir}}/granite
            Requires: cairo gee-0.8 glib-2.0 gio-unix-2.0 gobject-2.0
            """
        )

        assert pc_file.read_text(encoding=None) == expected_pc_file_content
