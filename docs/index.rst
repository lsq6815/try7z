try7z Documentation
===================

**try7z** is a 7-Zip frontend application for automatically extracting
password-protected archives using a user-saved password list.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules

Features
--------

* **Password Management**: Store and manage multiple passwords in a local JSON file
* **Automatic Extraction**: Try multiple passwords automatically until one works
* **Multiple Formats**: Support for ``.7z``, ``.zip``, and ``.rar`` archives
* **Bundled 7-Zip**: No external dependencies - 7-Zip executable is included
* **Cross-Platform**: Windows x64 ready; Linux and macOS paths prepared
  (requires placing the appropriate ``7zz`` binary manually)

Quick Start
-----------

Installation
^^^^^^^^^^^^

Install from source::

    pip install .

Or for development::

    pip install -e ".[dev]"

Basic Usage
^^^^^^^^^^^

Add passwords::

    $ try7z add "my_password"
    $ try7z add "pwd1" "pwd2" "pwd3"

List stored passwords::

    $ try7z list

Extract an archive::

    $ try7z extract path/to/archive.7z

With custom output directory::

    $ try7z extract path/to/archive.7z -o output_dir

API Reference
-------------

See :doc:`modules` for complete API documentation.

Command Reference
-----------------

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Command
     - Description
   * - ``add <password> ...``
     - Add one or more passwords to the stored list
   * - ``remove <password> ...``
     - Remove passwords by their value
   * - ``remove -i <index> ...``
     - Remove passwords by index (from ``list`` command)
   * - ``list``
     - Display all stored passwords with 1-based indices
   * - ``clear``
     - Remove all stored passwords (with confirmation)
   * - ``clear -f``
     - Clear all passwords without confirmation
   * - ``path``
     - Show the location of the passwords file
   * - ``edit``
     - Open passwords file in the default editor
   * - ``extract <archive>``
     - Extract an archive using stored passwords

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
