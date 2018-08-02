# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008 - 2014 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.


"""
Show a dialog with available fonts.
"""

from PyQt5.QtCore import (
    QRegExp,
    QSettings,
    QSize,
    Qt,
)
from PyQt5.QtWidgets import (
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

import app
import log
import qutil
import widgets.dialog
from widgets.lineedit import LineEdit
import fonts

from . import (
    textfonts,
    musicfonts
)


def show_available_fonts(mainwin, info):
    """Display a dialog with the available fonts of LilyPond specified by info."""
    dlg = ShowFontsDialog(mainwin, info)
    qutil.saveDialogSize(dlg, "engrave/tools/available-fonts/dialog/size", QSize(640, 400))
    dlg.show()


class ShowFontsDialog(widgets.dialog.Dialog):
    """Dialog to show available fonts"""

    def __init__(self, parent, info):
        super(ShowFontsDialog, self).__init__(
            parent,
            buttons=('restoredefaults', 'close',),
        )
        self.reloadButton = self._buttonBox.button(
            QDialogButtonBox.RestoreDefaults)
        self.reloadButton.setEnabled(False)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowModality(Qt.NonModal)
        self.tabWidget = QTabWidget(self)
        self.setMainWidget(self.tabWidget)

        self.lilypond_info = info
        self.available_fonts = fonts.available(info)

        self.createTabs()
        app.translateUI(self)
        self.loadSettings()

        self.connectSignals()
        if not self.available_fonts.text_fonts().is_loaded():
            self.font_tree_tab.display_waiting()
            self.available_fonts.text_fonts().load_fonts(self.logWidget)
        else:
            self.populate_widgets()

    def createTabs(self):

        available_fonts = self.available_fonts.text_fonts()

        def create_log():
            # Show original log
            self.logTab = QWidget()
            self.logWidget = log.Log(self.logTab)
            self.logLabel = QLabel()
            logLayout = QVBoxLayout()
            logLayout.addWidget(self.logLabel)
            logLayout.addWidget(self.logWidget)
            self.logTab.setLayout(logLayout)
            self.tabWidget.addTab(self.logTab, _("LilyPond output"))

        def create_music_fonts():
            # Show music font results
            self.musicFontsTab = mfTab = QWidget()
            self.musicFontsCountLabel = mfCountLabel = QLabel(mfTab)
            self.musicFontsInstallButton = mfInstallButton = QPushButton(mfTab)
            self.musicFontRemoveButton = mfRemoveButton = QPushButton(mfTab)
            self.musicFontRemoveButton.setEnabled(False)
            self.musicFontsSplitter = mfSplitter = QSplitter(mfTab)
            mfSplitter.setOrientation(Qt.Vertical)
            self.musicFontsView = mfView = QTreeView(mfSplitter)
            self.musicFontPreview = QTextEdit(mfSplitter)
            self.musicFontPreview.setHtml("Placeholder for score sample")
            musicButtonLayout = mbl = QHBoxLayout()
            mbl.addWidget(mfCountLabel)
            mbl.addStretch()
            mbl.addWidget(mfRemoveButton)
            mbl.addWidget(mfInstallButton)
            musicLayout = ml = QVBoxLayout()
            ml.addLayout(mbl)
            ml.addWidget(mfSplitter)
            mfSplitter.addWidget(mfView)
            mfSplitter.addWidget(self.musicFontPreview)
            mfTab.setLayout(ml)
            self.tabWidget.addTab(mfTab, _("Music Fonts"))

        def create_misc():
            # Show various fontconfig information
            self.miscTab = QWidget()
            self.miscTreeView = QTreeView(self.miscTab)
            self.miscTreeView.setHeaderHidden(True)
            self.miscLabel = QLabel()
            miscLayout = QVBoxLayout()
            miscLayout.addWidget(self.miscLabel)
            miscLayout.addWidget(self.miscTreeView)
            self.miscTab.setLayout(miscLayout)
            self.tabWidget.addTab(self.miscTab, _("Miscellaneous"))
            self.miscModel = available_fonts.miscModel
            self.miscTreeView.setModel(self.miscModel)

        create_log()
        # Show Text Font results
        self.font_tree_tab = textfonts.TextFontsWidget(self.available_fonts)
        self.tabWidget.addTab(self.font_tree_tab, _("Text Fonts"))

        create_music_fonts()
        create_misc()

    def connectSignals(self):
        self.available_fonts.text_fonts().loaded.connect(self.populate_widgets)
        self.finished.connect(self.saveSettings)
        self.reloadButton.clicked.connect(self.reload)
        self.musicFontsInstallButton.clicked.connect(self.install_music_fonts)

    def translateUI(self):
        self.setWindowTitle(app.caption(_("Available Fonts")))
        self.reloadButton.setText(_("&Reload"))
        self.logLabel.setText(_("LilyPond output of -dshow-available-options"))
        self.miscLabel.setText(_("Fontconfig data:"))
        self.musicFontRemoveButton.setText(_("Remove..."))
        self.musicFontRemoveButton.setToolTip(_("Remove selected music font"))
        self.musicFontsInstallButton.setText(_("Install..."))
        self.musicFontsInstallButton.setToolTip(
            _("Link fonts from a directory to the current LilyPond installation"))

    def loadSettings(self):
        s = QSettings()
        self.load_font_tree_column_width(s)
        s.beginGroup('available-fonts-dialog')
        # TODO: The following doesn't work so we can't restore
        # the layout of the splitter yet.
#        self.musicFontsSplitter.restoreState(
#            s.value('music-font-splitter-sizes').toByteArray()
#        )

    def saveSettings(self):
        s = QSettings()
        s.beginGroup('available-fonts-dialog')
        s.setValue('music-fonts-splitter-sizes',
            self.musicFontsSplitter.saveState())
        s.setValue('col-width', self.font_tree_tab.tree_view.columnWidth(0))

    def install_music_fonts(self):
        """'Install' music fonts from a directory (structure) by
        linking fonts into the LilyPond installation's font
        directories (otf and svg)."""

        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.Directory)
        if not dlg.exec():
            return

        installed = self.available_fonts.music_fonts()
        root_dir = dlg.selectedFiles()[0]
        from . import musicfonts
        repo = musicfonts.MusicFontRepo(root_dir)
        repo.flag_for_install(installed)

        # QUESTION: Do we need a message dialog to confirm/cancel installation?
        # repo.installable_fonts.item_model() is an item model like the one
        # we use for the music font display, but contains only the installable
        # font entries.

        try:
            repo.install_flagged(installed)
        except musicfonts.MusicFontPermissionException as e:
            # TODO: Show dialog or other handling, see #1083
            msg_box = QMessageBox()
            msg_box.setText(_("Fonts could not be installed!"))
            msg_box.setInformativeText(
            _("Installing fonts in the LilyPond installation " +
              "appears to require administrator privileges on " +
              "your system and can unfortunately not be handled " +
              "by Frescobaldi,"))
            msg_box.setDetailedText("{}".format(e))
            msg_box.exec()

    def load_font_tree_column_width(self, s):
        """Load column widths for fontTreeView,
        factored out because it has to be done upon reload too."""
        s.beginGroup('available-fonts-dialog')
        self.font_tree_tab.tree_view.setColumnWidth(0, int(s.value('col-width', 200)))

    def populate_widgets(self):
        """Populate widgets."""
        self.load_font_tree_column_width(QSettings())
        self.tabWidget.setCurrentIndex(1)
        self.font_tree_tab.display_count()
        self.font_tree_tab.refresh_filter_edit()
        self.font_tree_tab.filter_edit.setFocus()
        self.musicFontsModel = mfModel = self.available_fonts.music_fonts().item_model()
        mfView = self.musicFontsView
        mfView.setModel(mfModel)
        mfView.selectionModel().selectionChanged.connect(
            self.slot_music_fonts_selection_changed)
        self.reloadButton.setEnabled(True)

    def reload(self):
        """Refresh font list by running LilyPond"""
        self.tabWidget.setCurrentIndex(0)
        self.logWidget.clear()
        # We're connected to the 'loaded' signal
        self.available_fonts.text_fonts().load_fonts(self.logWidget)

    def slot_music_fonts_selection_changed(self, new, old):
        """Show a new score example with the selected music font"""
        font_family =new.indexes()[0].data()
        self.musicFontRemoveButton.setEnabled(len(new.indexes()) > 0)
        print("Selected:", font_family)
        print("Would now create/display score example")