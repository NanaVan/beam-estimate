#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import os, re, sqlite3, glob, json

class gen_database():
    '''Read LiseCute++ files to get production of nuclei'''
    def __init__(self):
        try:
            if os.path.exists("./web/dist/nuclei_data.sqlite"):
                os.remove("./web/dist/nuclei_data.sqlite")
            self.conn = sqlite3.connect("./web/dist/nuclei_data.sqlite")
            self.cur = self.conn.cursor()
            self.cur.execute('''CREATE TABLE TOTALNUCLEIDATA
            (A          INT         NOT NULL,
            ELEMENT     CHAR(2)     NOT NULL,
            Z           INT         NOT NULL,
            HALFLIFE    TEXT
            );''')
            with open("./nubase2020.txt") as nubase:
                for _ in '_'*25:
                    nubase.readline()
                for l in nubase:
                    # skip the isomers
                    if int(l[7]) != 0:
                        continue
                    A, Z, element = int(l[:3]), int(l[4:7]), re.split('(\d+)', l[11:16])[-1][:2]
                    element = element[0] if element[1]==' ' else element
                    stubs = l[69:80].split()
                    half_life = stubs[0].rstrip('#') if len(stubs)>0 else 'n/a'
                    half_life += ' ' + stubs[1] if (half_life[-1].isdigit() and len(stubs)>1) else ""
                    self.cur.execute("INSERT INTO TOTALNUCLEIDATA(A,ELEMENT,Z,HALFLIFE) VALUES (?,?,?,?)", (A, element, Z, half_life))
            self.conn.commit()
        except FileNotFoundError:
            print("Error: cannot find the files of nubase2020!")

    def get_subfolders(self, folder):
        subfolders = []
        for item in os.listdir(folder):
            item_path = os.path.join(folder, item)
            if os.path.isdir(item_path):
                subfolders.append(item_path)
        return subfolders

    def read_pf(self, file_folders):
        '''
        read .lpp files in assigned folder for projectile fragmentation channel
        return 2 json files for file information and nuclei information
        file_info = {'file_name1': {primary_beam, beam_energy, target_thickness}, 'file_name2': {primary_beam, beam_energy, target_thickness} ...}
        nuclei_info = {'nuclei1': {'file_name1': yield, 'file_name2': yield, ...}, 'nuclei2': {'file_name1': yield, ...}}
        return table PFDATA for nuclei of maximum yield

        yield = sum of different charge state yield
        '''
        nuclei_dict = {}
        file_dict = {}
        self.cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='PFDATA'")
        if self.cur.fetchone()[0] == 1:
            self.cur.execute("DROP TABLE PFDATA")
            self.conn.commit()
        self.cur.execute('''CREATE TABLE IF NOT EXISTS PFDATA 
                (A          INT         NOT NULL,
                ELEMENT     CHAR(2)     NOT NULL,
                NUCLEI      TEXT        NOT NULL,
                YIELD       REAL,
                FILENAME    TEXT,
                BEAM        TEXT,
                ENERGY      REAL,
                THICKNESS   REAL);''')
        self.cur.execute("DELETE FROM PFDATA")
        folders = self.get_subfolders(file_folders)
        files = []
        for folder in folders:
            files += glob.glob(folder+'/*.lpp')
        i = 0
        for file_address in files:
            if os.path.getsize(file_address) <= 71200:
                if 'error' in file_dict:
                    file_dict['error'].append(file_address)
                else:
                    file_dict['error'] = [file_address]
                continue
            with open(file_address) as lpp:
                file_name = '_'.join(os.path.basename(file_address).split('_')[:5])
                self.cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='temp_file'")
                if self.cur.fetchone()[0] == 1:
                    self.cur.execute("DROP TABLE temp_file")
                    self.conn.commit()
                self.cur.execute('''CREATE TABLE IF NOT EXISTS temp_file
                        (A          INT         NOT NULL,
                        ELEMENT     CHAR(2)     NOT NULL,
                        NUCLEI      TEXT        NOT NULL,
                        YIELD       REAL,
                        FILENAME    TEXT,
                        BEAM        TEXT,
                        ENERGY      REAL,
                        THICKNESS   REAL);''')
                while True:
                    line = lpp.readline().strip()
                    if line == "[settings]":
                        primary_beam = lpp.readline().strip().split()[2]
                        primary_energy = lpp.readline().strip().split()[2]
                    elif line == "[target]":
                        lpp.readline()
                        target_thickness = lpp.readline().strip().split()[3].split(',')[1]
                    elif line == "[Calculations]":
                        break
                    else:
                        pass
                # save file information
                file_dict[file_name] = {'primary_beam': primary_beam, 'primary_energy': primary_energy, 'target_thickness': target_thickness}
                for line in lpp:
                    segment = line.strip().split(',')[0].split()
                    A, element, _ = re.split("([A-Z][a-z]?)", segment[0])
                    self.cur.execute("INSERT INTO temp_file (A, ELEMENT, NUCLEI, YIELD, FILENAME, BEAM, ENERGY, THICKNESS) VALUES (?,?,?,?,?,?,?,?)", (A, element, A+element, segment[-1][1:], file_name, primary_beam, primary_energy, target_thickness))
                # reset yield for multiple charge state channels
                result = self.cur.execute("SELECT sum(YIELD), NUCLEI FROM temp_file GROUP BY NUCLEI").fetchall()
                self.cur.executemany("UPDATE temp_file SET YIELD=? WHERE NUCLEI=?", result)
                self.cur.executescript('''
                        CREATE TABLE TEMPTABLE as SELECT DISTINCT * FROM temp_file;
                        DROP TABLE temp_file;
                        ALTER TABLE TEMPTABLE RENAME TO temp_file;''')
                self.conn.commit()
                # save nuclei information
                for nuclei in result:
                    if nuclei[-1] in nuclei_dict:
                        nuclei_dict[nuclei[-1]][file_name] = nuclei[0]
                    else:
                        nuclei_dict[nuclei[-1]] = {file_name: nuclei[0]}
                # sort for the maximum yield for each nuclei
                self.cur.execute('''INSERT INTO PFDATA (A, ELEMENT, NUCLEI, YIELD, FILENAME, BEAM, ENERGY, THICKNESS) \
                            SELECT A, ELEMENT, NUCLEI, YIELD, FILENAME, BEAM, ENERGY, THICKNESS FROM temp_file;''')
                self.conn.commit()
                result = self.cur.execute("SELECT max(YIELD), FILENAME, BEAM, ENERGY, THICKNESS, NUCLEI FROM PFDATA GROUP BY NUCLEI").fetchall()
                self.cur.executemany("UPDATE PFDATA SET YIELD=?, FILENAME=?, BEAM=?, ENERGY=?, THICKNESS=? WHERE NUCLEI=?", result)
                self.cur.executescript("""
                        CREATE TABLE TEMPTABLE as SELECT DISTINCT * FROM PFDATA;
                        DROP TABLE PFDATA;
                        ALTER TABLE TEMPTABLE RENAME TO PFDATA;""")
                self.conn.commit()
            i += 1
            print('#{:}, file: {:}'.format(i, file_name))
            self.cur.execute("DROP TABLE temp_file")
        with open('pf_nuclei.json', 'w') as f:
            json.dump(nuclei_dict, f, indent=4)
        with open('pf_file.json', 'w') as f:
            json.dump(file_dict, f, indent=4)
        print('finised!')

    def read_fission(self, file_folder):
        '''
        read .lpp files in assigned folder for fission channel
        return 2 json files for file information and nuclei information
        file_info = {'file_name1': {primary_beam, beam_energy, target_thickness}, 'file_name2': {primary_beam, beam_energy, target_thickness} ...}
        nuclei_info = {'nuclei1': {'file_name1': yield, 'file_name2': yield, ...}, 'nuclei2': {'file_name1': yield, ...}}
        return table FISSIONDATA for nuclei of maximum yield

        yield = sum of low/mid/high channel yield + different charge state yield
        '''
        nuclei_dict = {}
        file_dict = {}
        self.cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='FISSIONDATA'")
        if self.cur.fetchone()[0] == 1:
            self.cur.execute("DROP TABLE FISSIONDATA")
            self.conn.commit()
        self.cur.execute('''CREATE TABLE IF NOT EXISTS FISSIONDATA 
                (A          INT         NOT NULL,
                ELEMENT     CHAR(2)     NOT NULL,
                NUCLEI      TEXT        NOT NULL,
                YIELD       REAL,
                FILENAME    TEXT,
                BEAM        TEXT,
                ENERGY      REAL,
                THICKNESS   REAL);''')
        self.cur.execute("DELETE FROM FISSIONDATA")
        files = glob.glob(file_folder + '*.lpp')
        i = 0
        for file_address in files:
            if os.path.getsize(file_address) <= 71200:
                if 'error' in file_dict:
                    file_dict['error'].append(file_address)
                else:
                    file_dict['error'] = [file_address]
                continue
            with open(file_address) as lpp:
                file_name = '_'.join(os.path.basename(file_address).split('_')[:5])
                self.cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='temp_file'")
                if self.cur.fetchone()[0] == 1:
                    self.cur.execute("DROP TABLE temp_file")
                    self.conn.commit()
                self.cur.execute('''CREATE TABLE IF NOT EXISTS temp_file
                        (A          INT         NOT NULL,
                        ELEMENT     CHAR(2)     NOT NULL,
                        NUCLEI      TEXT        NOT NULL,
                        YIELD       REAL,
                        FILENAME    TEXT,
                        BEAM        TEXT,
                        ENERGY      REAL,
                        THICKNESS   REAL);''')
                while True:
                    line = lpp.readline().strip()
                    if line == "[settings]":
                        primary_beam = lpp.readline().strip().split()[2]
                        primary_energy = lpp.readline().strip().split()[2]
                    elif line == "[target]":
                        lpp.readline()
                        target_thickness = lpp.readline().strip().split()[3].split(',')[1]
                    elif line == "[Calculations]":
                        break
                    else:
                        pass
                # save file information
                file_dict[file_name] = {'primary_beam': primary_beam, 'primary_energy': primary_energy, 'target_thickness': target_thickness}
                for line in lpp:
                    segment = line.strip().split(',')[0].split()
                    A, element, _ = re.split("([A-Z][a-z]?)", segment[0])
                    self.cur.execute("INSERT INTO temp_file (A, ELEMENT, NUCLEI, YIELD, FILENAME, BEAM, ENERGY, THICKNESS) VALUES (?,?,?,?,?,?,?,?)", (A, element, A+element, segment[-1][1:], file_name, primary_beam, primary_energy, target_thickness))
                # reset yield for multiple reaction channels
                result = self.cur.execute("SELECT sum(YIELD), NUCLEI FROM temp_file GROUP BY NUCLEI").fetchall()
                self.cur.executemany("UPDATE temp_file SET YIELD=? WHERE NUCLEI=?", result)
                self.cur.executescript('''
                        CREATE TABLE TEMPTABLE as SELECT DISTINCT * FROM temp_file;
                        DROP TABLE temp_file;
                        ALTER TABLE TEMPTABLE RENAME TO temp_file;''')
                self.conn.commit()
                # save nuclei information
                for nuclei in result:
                    if nuclei[-1] in nuclei_dict:
                        nuclei_dict[nuclei[-1]][file_name] = nuclei[0]
                    else:
                        nuclei_dict[nuclei[-1]] = {file_name: nuclei[0]}
                # sort for the maximum yield for each nuclei
                self.cur.execute('''INSERT INTO FISSIONDATA (A, ELEMENT, NUCLEI, YIELD, FILENAME, BEAM, ENERGY, THICKNESS) \
                            SELECT A, ELEMENT, NUCLEI, YIELD, FILENAME, BEAM, ENERGY, THICKNESS FROM temp_file;''')
                self.conn.commit()
                result = self.cur.execute("SELECT max(YIELD), FILENAME, BEAM, ENERGY, THICKNESS, NUCLEI FROM FISSIONDATA GROUP BY NUCLEI").fetchall()
                self.cur.executemany("UPDATE FISSIONDATA SET YIELD=?, FILENAME=?, BEAM=?, ENERGY=?, THICKNESS=? WHERE NUCLEI=?", result)
                self.cur.executescript("""
                        CREATE TABLE TEMPTABLE as SELECT DISTINCT * FROM FISSIONDATA;
                        DROP TABLE FISSIONDATA;
                        ALTER TABLE TEMPTABLE RENAME TO FISSIONDATA;""")
                self.conn.commit()
            i += 1
            print('#{:}, file: {:}'.format(i, file_name))
            self.cur.execute("DROP TABLE temp_file")
        with open('fission_nuclei.json', 'w') as f:
            json.dump(nuclei_dict, f, indent=4)
        with open('fission_file.json', 'w') as f:
            json.dump(file_dict, f, indent=4)
        print('finised!')


database_maker = gen_database()
# save pf result
database_maker.read_pf('F:/JiaohongyangFiles/SRing/2024-7-23_PF/Results/')
# save fission result
database_maker.read_fission('F:/JiaohongyangFiles/SRing/2024-7-20_Fission/Results/238U_f_20240723/')
print('finished all!')
