#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import os, re, sqlite3, glob, json
import numpy as np

El = ['H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca']

class gen_database():
    '''Read LiseCute++ files to get production of nuclei'''
    def __init__(self, renew_all=True):
        try:
            if os.path.exists("./web/dist/nuclei_data.sqlite") or renew_all:
                os.remove("./web/dist/nuclei_data.sqlite")
            self.conn = sqlite3.connect("./web/dist/nuclei_data.sqlite")
            self.cur = self.conn.cursor()
            self.cur.execute('''CREATE TABLE TOTALNUCLEIDATA
            (A          INT         NOT NULL,
            ELEMENT     CHAR(2)     NOT NULL,
            Z           INT         NOT NULL,
            HALFLIFE    TEXT,
            BR          TEXT
            );''')
            with open("./nubase2020.txt") as nubase:
                for _ in '_'*25:
                    nubase.readline()
                for l in nubase:
                    # skip the isomers
                    if int(l[7]) != 0:
                        continue
                    A, Z, element, br_info = int(l[:3]), int(l[4:7]), re.split('(\d+)', l[11:16])[-1][:2], l[119:-1]
                    element = element[0] if element[1]==' ' else element
                    stubs = l[69:80].split()
                    half_life = stubs[0].rstrip('#') if len(stubs)>0 else 'n/a'
                    half_life += ' ' + stubs[1] if (half_life[-1].isdigit() and len(stubs)>1) else ""
                    self.cur.execute("INSERT INTO TOTALNUCLEIDATA(A,ELEMENT,Z,HALFLIFE,BR) VALUES (?,?,?,?,?)", (A, element, Z, half_life, br_info))
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
        file_info = {'file_name1': {primary_beam, beam_energy, beam_intensity, Brho, total_yield, target_thickness}, 'file_name2': {primary_beam, beam_energy, beam_intensity, Brho, total_yield, target_thickness} ...}
        nuclei_info = {'nuclei1': {'file_name1': {'yield': yield, 'purity': yield/total_yield, 'charge_yield'}, 'file_name2': yield, ...}, 'nuclei2': {'file_name1': {'yield': yield, 'purity': yield/total_yield, 'charge_yield'}}, ...}
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
                PURE        REAL,
                FILENAME    TEXT,
                BEAM        TEXT,
                ENERGY      REAL,
                INTENSITY   REAL,
                TARGET      TEXT,
                THICKNESS   REAL,
                BRHO        REAL,
                CHARGEYIELD TEXT);''')
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
                        PURE        REAL,
                        FILENAME    TEXT,
                        BEAM        TEXT,
                        ENERGY      REAL,
                        INTENSITY   REAL,
                        TARGET      TEXT,
                        THICKNESS   REAL,
                        BRHO        REAL,
                        IONCHARGE   INT,
                        IONYIELD    REAL,
                        CHARGEYIELD TEXT);''')
                while True:
                    line = lpp.readline().strip()
                    if line == "[settings]":
                        primary_beam = lpp.readline().strip().split(';')[0].strip().split('=')[-1].replace(' ', '')
                        primary_energy = lpp.readline().strip().split()[2]
                        primary_intensity = lpp.readline().strip().split()[2]
                    elif line == "[target]":
                        target_Z, _, target_mass = lpp.readline().strip().split()[3].split(',')[1:]
                        target = "{:d}{:}".format(int(np.round(float(target_mass))), El[int(target_Z)-1])
                        target_thickness = lpp.readline().strip().split()[3].split(',')[1]
                    elif line == "[D6_DipoleSettings]":
                        Brho = float(lpp.readline().strip().split()[2]) # Tm
                    elif line == "[Calculations]":
                        break
                    else:
                        pass
                for line in lpp:
                    segment = line.strip().split(',')[0].split()
                    A, element, Q = re.split("([A-Z][a-z]?)", segment[0]+segment[-2][:-1])
                    self.cur.execute("INSERT INTO temp_file (A, ELEMENT, NUCLEI, FILENAME, BEAM, ENERGY, INTENSITY, TARGET, THICKNESS, BRHO, IONCHARGE, IONYIELD) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (A, element, A+element, file_name, primary_beam, primary_energy, primary_intensity, target, target_thickness, Brho, Q, segment[-1][1:]))
                # reset yield for multiple charge state channels
                result = self.cur.execute("SELECT sum(IONYIELD), NUCLEI FROM temp_file GROUP BY NUCLEI").fetchall()
                total_yield = self.cur.execute("SELECT sum(IONYIELD) FROM temp_file").fetchone()[0]
                result = [(item[0], item[0]/total_yield, 10, 1e3, \
                    ','.join(['{:}:{:}'.format(temp_QY[0], temp_QY[1]) for temp_QY in self.cur.execute("SELECT IONCHARGE, IONYIELD FROM temp_file WHERE NUCLEI=?", (item[1],)).fetchall()]), \
                    item[1]) for item in result]
                self.cur.executemany("UPDATE temp_file SET YIELD=?, PURE=?, IONCHARGE=?, IONYIELD=?, CHARGEYIELD=? WHERE NUCLEI=?", result)
                self.cur.executescript('''
                        CREATE TABLE TEMPTABLE as SELECT DISTINCT * FROM temp_file;
                        DROP TABLE temp_file;
                        ALTER TABLE TEMPTABLE RENAME TO temp_file;''')
                self.conn.commit()
                # save file information
                file_dict[file_name] = {'primary_beam': primary_beam, 'primary_energy': primary_energy, 'primary_intensity': primary_intensity, 'total_yield': total_yield, 'target': target, 'target_thickness': target_thickness, 'Brho': Brho}
                # save nuclei information
                for nuclei in result:
                    if nuclei[-1] in nuclei_dict:
                        nuclei_dict[nuclei[-1]][file_name] = {'yield': nuclei[0], 'purity': nuclei[0]/total_yield, 'charge_yield': nuclei[-2]}
                    else:
                        nuclei_dict[nuclei[-1]] = {file_name: {'yield': nuclei[0], 'purity': nuclei[0]/total_yield, 'charge_yield': nuclei[-2]}}
                # sort for the maximum yield for each nuclei
                self.cur.execute('''INSERT INTO PFDATA (A, ELEMENT, NUCLEI, YIELD, PURE, FILENAME, BEAM, ENERGY, INTENSITY, TARGET, THICKNESS, BRHO, CHARGEYIELD) \
                            SELECT A, ELEMENT, NUCLEI, YIELD, PURE, FILENAME, BEAM, ENERGY, INTENSITY, TARGET, THICKNESS, BRHO, CHARGEYIELD FROM temp_file;''')
                self.conn.commit()
                result = self.cur.execute("SELECT max(YIELD), PURE, FILENAME, BEAM, ENERGY, INTENSITY, TARGET, THICKNESS, BRHO, CHARGEYIELD, NUCLEI FROM PFDATA GROUP BY NUCLEI").fetchall()
                self.cur.executemany("UPDATE PFDATA SET YIELD=?, PURE=?, FILENAME=?, BEAM=?, ENERGY=?, INTENSITY=?, TARGET=?, THICKNESS=?, BRHO=?, CHARGEYIELD=? WHERE NUCLEI=?", result)
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

    def read_fission_IFN(self, file_folder):
        '''
        fission model IFN
        read .lpp files in assigned folder for fission channel
        return 2 json files for file information and nuclei information
        file_info = {'file_name1': {primary_beam, beam_energy, beam_intensity, Brho, total_yield, target_thickness}, 'file_name2': {primary_beam, beam_energy, beam_intensity, Brho, total_yield, target_thickness} ...}
        nuclei_info = {'nuclei1': {'file_name1': {'yield': yield, 'purity': yield/total_yield, 'charge_yield'}, 'file_name2': yield, ...}, 'nuclei2': {'file_name1': {'yield': yield, 'purity': yield/total_yield, 'charge_yield'}}, ...}
        return table FISSIONDATA_IFN for nuclei of maximum yield

        yield = sum of low/mid/high channel yield + different charge state yield
        '''
        nuclei_dict = {}
        file_dict = {}
        self.cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='FISSIONDATA_IFN'")
        if self.cur.fetchone()[0] == 1:
            self.cur.execute("DROP TABLE FISSIONDATA_IFN")
            self.conn.commit()
        self.cur.execute('''CREATE TABLE IF NOT EXISTS FISSIONDATA_IFN 
                (A          INT         NOT NULL,
                ELEMENT     CHAR(2)     NOT NULL,
                NUCLEI      TEXT        NOT NULL,
                YIELD       REAL,
                PURE        REAL,
                FILENAME    TEXT,
                BEAM        TEXT,
                ENERGY      REAL,
                INTENSITY   REAL,
                TARGET      TEXT,
                THICKNESS   REAL,
                BRHO        REAL,
                CHARGEYIELD TEXT);''')
        self.cur.execute("DELETE FROM FISSIONDATA_IFN")
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
                        PURE        REAL,
                        FILENAME    TEXT,
                        BEAM        TEXT,
                        ENERGY      REAL,
                        INTENSITY   REAL,
                        TARGET      TEXT,
                        THICKNESS   REAL,
                        BRHO        REAL,
                        IONCHARGE   INT,
                        IONYIELD    REAL,
                        CHARGEYIELD TEXT);''')
                while True:
                    line = lpp.readline().strip()
                    if line == "[settings]":
                        primary_beam = lpp.readline().strip().split(';')[0].strip().split('=')[-1].replace(' ', '')
                        primary_energy = lpp.readline().strip().split()[2]
                        primary_intensity = lpp.readline().strip().split()[2]
                    elif line == "[target]":
                        target_Z, _, target_mass = lpp.readline().strip().split()[3].split(',')[1:]
                        target = "{:d}{:}".format(int(np.round(float(target_mass))), El[int(target_Z)-1])
                        target_thickness = lpp.readline().strip().split()[3].split(',')[1]
                    elif line == "[D6_DipoleSettings]":
                        Brho = float(lpp.readline().strip().split()[2]) # Tm
                    elif line == "[Calculations]":
                        break
                    else:
                        pass
                for line in lpp:
                    segment = line.strip().split(',')[0].split()
                    A, element, Q = re.split("([A-Z][a-z]?)", segment[0]+segment[-2][:-1])
                    self.cur.execute("INSERT INTO temp_file (A, ELEMENT, NUCLEI, FILENAME, BEAM, ENERGY, INTENSITY, TARGET, THICKNESS, BRHO, IONCHARGE, IONYIELD) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (A, element, A+element, file_name, primary_beam, primary_energy, primary_intensity, target, target_thickness, Brho, Q, segment[-1][1:]))
                # reset yield for multiple reaction channels for each charge state
                result = self.cur.execute("SELECT sum(IONYIELD), NUCLEI, IONCHARGE FROM temp_file GROUP BY NUCLEI, IONCHARGE").fetchall()
                #print(result)
                self.cur.executemany("UPDATE temp_file SET IONYIELD=? WHERE NUCLEI=? AND IONCHARGE=?", result)
                self.cur.executescript('''
                        CREATE TABLE TEMPTABLE as SELECT DISTINCT * FROM temp_file;
                        DROP TABLE temp_file;
                        ALTER TABLE TEMPTABLE RENAME TO temp_file;''')
                self.conn.commit()
                # reset yield for multiple charge state channels
                result = self.cur.execute("SELECT sum(IONYIELD), NUCLEI FROM temp_file GROUP BY NUCLEI").fetchall()
                #print(result)
                total_yield = self.cur.execute("SELECT sum(IONYIELD) FROM temp_file").fetchone()[0]
                result = [(item[0], item[0]/total_yield, 10, 1e3, \
                    ','.join(['{:}:{:}'.format(temp_QY[0], temp_QY[1]) for temp_QY in self.cur.execute("SELECT IONCHARGE, IONYIELD FROM temp_file WHERE NUCLEI=?", (item[1],)).fetchall()]),\
                        item[1]) for item in result]
                self.cur.executemany("UPDATE temp_file SET YIELD=?, PURE=?, IONCHARGE=?, IONYIELD=?, CHARGEYIELD=? WHERE NUCLEI=?", result)
                self.cur.executescript('''
                        CREATE TABLE TEMPTABLE as SELECT DISTINCT * FROM temp_file;
                        DROP TABLE temp_file;
                        ALTER TABLE TEMPTABLE RENAME TO temp_file;''')
                self.conn.commit()
                # save file information
                file_dict[file_name] = {'primary_beam': primary_beam, 'primary_energy': primary_energy, 'primary_intensity': primary_intensity, 'total_yield': total_yield, 'target': target, 'target_thickness': target_thickness}
                # save nuclei information
                for nuclei in result:
                    if nuclei[-1] in nuclei_dict:
                        nuclei_dict[nuclei[-1]][file_name] = {'yield': nuclei[0], 'purity': nuclei[0]/total_yield, 'charge_yield': nuclei[-2]}
                    else:
                        nuclei_dict[nuclei[-1]] = {file_name: {'yield': nuclei[0], 'purity': nuclei[0]/total_yield, 'charge_yield': nuclei[-2]}}
                # sort for the maximum yield for each nuclei
                self.cur.execute('''INSERT INTO FISSIONDATA_IFN (A, ELEMENT, NUCLEI, YIELD, PURE, FILENAME, BEAM, ENERGY, INTENSITY, TARGET, THICKNESS, BRHO, CHARGEYIELD) \
                            SELECT A, ELEMENT, NUCLEI, YIELD, PURE, FILENAME, BEAM, ENERGY, INTENSITY, TARGET, THICKNESS, BRHO, CHARGEYIELD FROM temp_file;''')
                self.conn.commit()
                result = self.cur.execute("SELECT max(YIELD), PURE, FILENAME, BEAM, ENERGY, INTENSITY, TARGET, THICKNESS, BRHO, CHARGEYIELD, NUCLEI FROM FISSIONDATA_IFN GROUP BY NUCLEI").fetchall()
                self.cur.executemany("UPDATE FISSIONDATA_IFN SET YIELD=?, PURE=?, FILENAME=?, BEAM=?, ENERGY=?, INTENSITY=?, TARGET=?, THICKNESS=?, BRHO=?, CHARGEYIELD=? WHERE NUCLEI=?", result)
                self.cur.executescript("""
                        CREATE TABLE TEMPTABLE as SELECT DISTINCT * FROM FISSIONDATA_IFN;
                        DROP TABLE FISSIONDATA_IFN;
                        ALTER TABLE TEMPTABLE RENAME TO FISSIONDATA_IFN;""")
                self.conn.commit()
            i += 1
            print('#{:}, file: {:}'.format(i, file_name))
            self.cur.execute("DROP TABLE temp_file")
        with open('fission_IFN_nuclei.json', 'w') as f:
            json.dump(nuclei_dict, f, indent=4)
        with open('fission_IFN_file.json', 'w') as f:
            json.dump(file_dict, f, indent=4)
        print('finised!')

    def read_fission_IMP(self, file_folder):
        '''
        fission model IMP-3Gaussian
        read .lpp files in assigned folder for fission channel
        return 2 json files for file information and nuclei information
        file_info = {'file_name1': {primary_beam, beam_energy, beam_intensity, Brho, total_yield, target_thickness}, 'file_name2': {primary_beam, beam_energy, beam_intensity, Brho, total_yield, target_thickness} ...}
        nuclei_info = {'nuclei1': {'file_name1': {'yield': yield, 'purity': yield/total_yield, 'charge_yield'}, 'file_name2': yield, ...}, 'nuclei2': {'file_name1': {'yield': yield, 'purity': yield/total_yield, 'charge_yield'}}, ...}
        return table FISSIONDATA_IMP for nuclei of maximum yield

        yield = sum of low/mid/high channel yield + different charge state yield
        '''
        nuclei_dict = {}
        file_dict = {}
        self.cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='FISSIONDATA_IMP'")
        if self.cur.fetchone()[0] == 1:
            self.cur.execute("DROP TABLE FISSIONDATA_IMP")
            self.conn.commit()
        self.cur.execute('''CREATE TABLE IF NOT EXISTS FISSIONDATA_IMP 
                (A          INT         NOT NULL,
                ELEMENT     CHAR(2)     NOT NULL,
                NUCLEI      TEXT        NOT NULL,
                YIELD       REAL,
                PURE        REAL,
                FILENAME    TEXT,
                BEAM        TEXT,
                ENERGY      REAL,
                INTENSITY   REAL,
                TARGET      TEXT,
                THICKNESS   REAL,
                BRHO        REAL,
                CHARGEYIELD TEXT);''')
        self.cur.execute("DELETE FROM FISSIONDATA_IMP")
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
                        PURE        REAL,
                        FILENAME    TEXT,
                        BEAM        TEXT,
                        ENERGY      REAL,
                        INTENSITY   REAL,
                        TARGET      TEXT,
                        THICKNESS   REAL,
                        BRHO        REAL,
                        IONCHARGE   INT,
                        IONYIELD    REAL,
                        CHARGEYIELD TEXT);''')
                while True:
                    line = lpp.readline().strip()
                    if line == "[settings]":
                        primary_beam = lpp.readline().strip().split(';')[0].strip().split('=')[-1].replace(' ', '')
                        primary_energy = lpp.readline().strip().split()[2]
                        primary_intensity = lpp.readline().strip().split()[2]
                    elif line == "[target]":
                        target_Z, _, target_mass = lpp.readline().strip().split()[3].split(',')[1:]
                        target = "{:d}{:}".format(int(np.round(float(target_mass))), El[int(target_Z)-1])
                        target_thickness = lpp.readline().strip().split()[3].split(',')[1]
                    elif line == "[D6_DipoleSettings]":
                        Brho = float(lpp.readline().strip().split()[2]) # Tm
                    elif line == "[Calculations]":
                        break
                    else:
                        pass
                for line in lpp:
                    segment = line.strip().split(',')[0].split()
                    A, element, Q = re.split("([A-Z][a-z]?)", segment[0]+segment[-2][:-1])
                    self.cur.execute("INSERT INTO temp_file (A, ELEMENT, NUCLEI, FILENAME, BEAM, ENERGY, INTENSITY, TARGET, THICKNESS, BRHO, IONCHARGE, IONYIELD) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (A, element, A+element, file_name, primary_beam, primary_energy, primary_intensity, target, target_thickness, Brho, Q, segment[-1][1:]))
                # reset yield for multiple reaction channels for each charge state
                result = self.cur.execute("SELECT sum(IONYIELD), NUCLEI, IONCHARGE FROM temp_file GROUP BY NUCLEI, IONCHARGE").fetchall()
                #print(result)
                self.cur.executemany("UPDATE temp_file SET IONYIELD=? WHERE NUCLEI=? AND IONCHARGE=?", result)
                self.cur.executescript('''
                        CREATE TABLE TEMPTABLE as SELECT DISTINCT * FROM temp_file;
                        DROP TABLE temp_file;
                        ALTER TABLE TEMPTABLE RENAME TO temp_file;''')
                self.conn.commit()
                # reset yield for multiple charge state channels
                result = self.cur.execute("SELECT sum(IONYIELD), NUCLEI FROM temp_file GROUP BY NUCLEI").fetchall()
                #print(result)
                total_yield = self.cur.execute("SELECT sum(IONYIELD) FROM temp_file").fetchone()[0]
                result = [(item[0], item[0]/total_yield, 10, 1e3, \
                    ','.join(['{:}:{:}'.format(temp_QY[0], temp_QY[1]) for temp_QY in self.cur.execute("SELECT IONCHARGE, IONYIELD FROM temp_file WHERE NUCLEI=?", (item[1],)).fetchall()]),\
                        item[1]) for item in result]
                self.cur.executemany("UPDATE temp_file SET YIELD=?, PURE=?, IONCHARGE=?, IONYIELD=?, CHARGEYIELD=? WHERE NUCLEI=?", result)
                self.cur.executescript('''
                        CREATE TABLE TEMPTABLE as SELECT DISTINCT * FROM temp_file;
                        DROP TABLE temp_file;
                        ALTER TABLE TEMPTABLE RENAME TO temp_file;''')
                self.conn.commit()
                # save file information
                file_dict[file_name] = {'primary_beam': primary_beam, 'primary_energy': primary_energy, 'primary_intensity': primary_intensity, 'total_yield': total_yield, 'target': target, 'target_thickness': target_thickness}
                # save nuclei information
                for nuclei in result:
                    if nuclei[-1] in nuclei_dict:
                        nuclei_dict[nuclei[-1]][file_name] = {'yield': nuclei[0], 'purity': nuclei[0]/total_yield, 'charge_yield': nuclei[-2]}
                    else:
                        nuclei_dict[nuclei[-1]] = {file_name: {'yield': nuclei[0], 'purity': nuclei[0]/total_yield, 'charge_yield': nuclei[-2]}}
                # sort for the maximum yield for each nuclei
                self.cur.execute('''INSERT INTO FISSIONDATA_IMP (A, ELEMENT, NUCLEI, YIELD, PURE, FILENAME, BEAM, ENERGY, INTENSITY, TARGET, THICKNESS, BRHO, CHARGEYIELD) \
                            SELECT A, ELEMENT, NUCLEI, YIELD, PURE, FILENAME, BEAM, ENERGY, INTENSITY, TARGET, THICKNESS, BRHO, CHARGEYIELD FROM temp_file;''')
                self.conn.commit()
                result = self.cur.execute("SELECT max(YIELD), PURE, FILENAME, BEAM, ENERGY, INTENSITY, TARGET, THICKNESS, BRHO, CHARGEYIELD, NUCLEI FROM FISSIONDATA_IMP GROUP BY NUCLEI").fetchall()
                self.cur.executemany("UPDATE FISSIONDATA_IMP SET YIELD=?, PURE=?, FILENAME=?, BEAM=?, ENERGY=?, INTENSITY=?, TARGET=?, THICKNESS=?, BRHO=?, CHARGEYIELD=? WHERE NUCLEI=?", result)
                self.cur.executescript("""
                        CREATE TABLE TEMPTABLE as SELECT DISTINCT * FROM FISSIONDATA_IMP;
                        DROP TABLE FISSIONDATA_IMP;
                        ALTER TABLE TEMPTABLE RENAME TO FISSIONDATA_IMP;""")
                self.conn.commit()
            i += 1
            print('#{:}, file: {:}'.format(i, file_name))
            self.cur.execute("DROP TABLE temp_file")
        with open('fission_IMP_nuclei.json', 'w') as f:
            json.dump(nuclei_dict, f, indent=4)
        with open('fission_IMP_file.json', 'w') as f:
            json.dump(file_dict, f, indent=4)
        print('finised!')


database_maker = gen_database()
## save pf result
database_maker.read_pf('./web/files/pf/')
## save fission result
database_maker.read_fission_IMP('./web/files/fission/IMP/')
database_maker.read_fission_IFN('./web/files/fission/IFN/')
print('finished all!')
