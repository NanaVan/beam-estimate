function rewriteDecayMode(str_DecayMode){
	return str_DecayMode.replace('B', 'β').replace('A', 'α').replace('+', '<sup>+</sup>').replace('-', '<sup>-</sup>').replace(';', '; ');
}

async function checkNuclei(){
	const [SQL, buf] = await Promise.all([
		initSqlJs({locateFile: file=> `/dist/${file}`}),
		fetch("/dist/nuclei_data.sqlite").then(res => res.arrayBuffer())
		// nuclei_data from NUBASE2020
	]);
	const db = new SQL.Database(new Uint8Array(buf));
	let stmt = db.prepare("SELECT ElEMENT, HALFLIFE, BR FROM TOTALNUCLEIDATA WHERE Z=$zval AND A=$aval");
	let result = stmt.get({'$zval': document.getElementById('atomic_number').value, '$aval': document.getElementById('mass_number').value});
	stmt.free();
	//console.log(result);
	if (Array.isArray(result) && result.length===0){
		document.getElementById('div_result').style.display = 'block';	
		document.getElementById('p_error0').style.display = 'block';
		document.getElementById('tab_nuclei').style.display = 'block';	
		document.getElementById('tab_nuclei').rows[0].cells[1].innerHTML = document.getElementById('mass_number').value;	
		document.getElementById('tab_nuclei').rows[1].cells[1].innerHTML = document.getElementById('atomic_number').value;	
		document.getElementById('tab_nuclei').rows[2].cells[1].innerHTML = 'unknown';	
		document.getElementById('tab_nuclei').rows[3].cells[1].innerHTML = 'unknown';
		document.getElementById('tab_nuclei').rows[4].cells[1].innerHTML = 'unknown';
	}else{
		document.getElementById('div_result').style.display = 'block';	
		document.getElementById('tab_nuclei').style.display = 'block';	
		document.getElementById('tab_nuclei').rows[0].cells[1].innerHTML = document.getElementById('mass_number').value;	
		document.getElementById('tab_nuclei').rows[1].cells[1].innerHTML = document.getElementById('atomic_number').value;	
		document.getElementById('tab_nuclei').rows[2].cells[1].innerHTML = result[0];	
		document.getElementById('tab_nuclei').rows[3].cells[1].innerHTML = result[1];
		document.getElementById('tab_nuclei').rows[4].cells[1].innerHTML = rewriteDecayMode(result[2]);
	}
	stmt = db.prepare("SELECT YIELD, CHARGEYIELD, PURE, BEAM, ENERGY, INTENSITY, BRHO, TARGET, THICKNESS, FILENAME FROM FISSIONDATA_IFN WHERE A=$aval AND ELEMENT=$eleval AND DPP=4");
	let result_fission_IFN_dpp4 = stmt.get({'$aval': document.getElementById('mass_number').value, '$eleval': result[0]});
	stmt.free();
	stmt = db.prepare("SELECT YIELD, CHARGEYIELD, PURE, BEAM, ENERGY, INTENSITY, BRHO, TARGET, THICKNESS, FILENAME FROM FISSIONDATA_IFN WHERE A=$aval AND ELEMENT=$eleval AND DPP=0.4");
	let result_fission_IFN_dpp04 = stmt.get({'$aval': document.getElementById('mass_number').value, '$eleval': result[0]});
	stmt.free();
	stmt = db.prepare("SELECT YIELD, CHARGEYIELD, PURE, BEAM, ENERGY, INTENSITY, BRHO, TARGET, THICKNESS, FILENAME FROM FISSIONDATA_IMP WHERE A=$aval AND ELEMENT=$eleval");
	let result_fission_IMP = stmt.get({'$aval': document.getElementById('mass_number').value, '$eleval': result[0]});
	stmt.free();
	stmt = db.prepare("SELECT YIELD, CHARGEYIELD, PURE, BEAM, ENERGY, INTENSITY, BRHO, TARGET, THICKNESS, FILENAME FROM PFDATA WHERE A=$aval AND ELEMENT=$eleval AND DPP=4");
	let result_pf_dpp4 = stmt.get({'$aval': document.getElementById('mass_number').value, '$eleval': result[0]});
	stmt.free();
	stmt = db.prepare("SELECT YIELD, CHARGEYIELD, PURE, BEAM, ENERGY, INTENSITY, BRHO, TARGET, THICKNESS, FILENAME FROM PFDATA WHERE A=$aval AND ELEMENT=$eleval AND DPP=0.4");
	let result_pf_dpp04 = stmt.get({'$aval': document.getElementById('mass_number').value, '$eleval': result[0]});
	stmt.free();

	let flag = 0;
	if (Array.isArray(result_pf_dpp4) && result_pf_dpp4.length===0 && Array.isArray(result_pf_dpp04) && result_pf_dpp04.length===0){
		flag += 1;
	}else{
		document.getElementById('tab_pfResult').style.display = 'block';
		if (Array.isArray(result_pf_dpp4) && result_pf_dpp4.length > 0){
			document.getElementById('tab_pfResult').rows[1].cells[1].innerHTML = result_pf_dpp4[0].toExponential(3).toString() + ' pps';
			console.log(result_pf_dpp4[1]);
			let pf_charge_dpp4_info = result_pf_dpp4[1].split(',');
			var pf_charge_dpp4_line = [];
			for (let item of pf_charge_dpp4_info){
				pf_charge_dpp4_line.push(item.split(':')[0]+'+: ' + Number(item.split(':')[1]).toExponential(3).toString() + ' pps');
			}
			document.getElementById('tab_pfResult').rows[2].cells[1].innerHTML = pf_charge_dpp4_line.join('<br/>');
			pf_purity_dpp4 = (result_pf_dpp4[2]*100).toFixed(3)
			if (pf_purity_dpp4 < 0.001){
				pf_purity_dpp4 = (result_pf_dpp4[2]*100).toExponential(3)
			}
			document.getElementById('tab_pfResult').rows[3].cells[1].innerHTML = pf_purity_dpp4.toString() + ' %';
			document.getElementById('tab_pfResult').rows[4].cells[1].innerHTML = result_pf_dpp4[3];
			document.getElementById('tab_pfResult').rows[5].cells[1].innerHTML = result_pf_dpp4[4].toString() + ' MeV/u' ;
			document.getElementById('tab_pfResult').rows[6].cells[1].innerHTML = result_pf_dpp4[5].toExponential(3).toString() + ' pps' ;
			document.getElementById('tab_pfResult').rows[7].cells[1].innerHTML = result_pf_dpp4[6] + ' Tm';
			document.getElementById('tab_pfResult').rows[8].cells[1].innerHTML = result_pf_dpp4[7];
			document.getElementById('tab_pfResult').rows[9].cells[1].innerHTML = '<span>' + result_pf_dpp4[8].toString() + ' mg/cm<sup>2</sup></span>';
			//console.log(result_pf[9]);
			document.getElementById('a_pf_4').href = '/files/pf/'+ result_pf_dpp4[3].match(/\d{2,3}[A-Za-z]{1,2}/g) + '/' + result_pf_dpp4[9] + '_Test_auto_Run.lpp'
		}else{
			document.getElementById('tab_pfResult').rows[1].cells[1].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[2].cells[1].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[3].cells[1].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[4].cells[1].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[5].cells[1].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[6].cells[1].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[7].cells[1].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[8].cells[1].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[9].cells[1].innerHTML = '-';
		}		
		if (Array.isArray(result_pf_dpp04) && result_pf_dpp04.length > 0){
			document.getElementById('tab_pfResult').rows[1].cells[2].innerHTML = result_pf_dpp04[0].toExponential(3).toString() + ' pps';
			console.log(result_pf_dpp04[1]);
			let pf_charge_dpp04_info = result_pf_dpp04[1].split(',');
			var pf_charge_dpp04_line = [];
			for (let item of pf_charge_dpp04_info){
				pf_charge_dpp04_line.push(item.split(':')[0]+'+: ' + Number(item.split(':')[1]).toExponential(3).toString() + ' pps');
			}
			document.getElementById('tab_pfResult').rows[2].cells[2].innerHTML = pf_charge_dpp04_line.join('<br/>');
			pf_purity_dpp04 = (result_pf_dpp04[2]*100).toFixed(3)
			if (pf_purity_dpp04 < 0.001){
				pf_purity_dpp04 = (result_pf_dpp04[2]*100).toExponential(3)
			}
			document.getElementById('tab_pfResult').rows[3].cells[2].innerHTML = pf_purity_dpp04.toString() + ' %';
			document.getElementById('tab_pfResult').rows[4].cells[2].innerHTML = result_pf_dpp04[3];
			document.getElementById('tab_pfResult').rows[5].cells[2].innerHTML = result_pf_dpp04[4].toString() + ' MeV/u' ;
			document.getElementById('tab_pfResult').rows[6].cells[2].innerHTML = result_pf_dpp04[5].toExponential(3).toString() + ' pps' ;
			document.getElementById('tab_pfResult').rows[7].cells[2].innerHTML = result_pf_dpp04[6] + ' Tm';
			document.getElementById('tab_pfResult').rows[8].cells[2].innerHTML = result_pf_dpp04[7];
			document.getElementById('tab_pfResult').rows[9].cells[2].innerHTML = '<span>' + result_pf_dpp04[8].toString() + ' mg/cm<sup>2</sup></span>';
			//console.log(result_pf[9]);
			document.getElementById('a_pf_04').href = '/files/pf/'+ result_pf_dpp04[3].match(/\d{2,3}[A-Za-z]{1,2}/g) + '/' + result_pf_dpp04[9] + '_Test_auto_Run.lpp'
		}else{
			document.getElementById('tab_pfResult').rows[1].cells[2].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[2].cells[2].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[3].cells[2].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[4].cells[2].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[5].cells[2].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[6].cells[2].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[7].cells[2].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[8].cells[2].innerHTML = '-';
			document.getElementById('tab_pfResult').rows[9].cells[2].innerHTML = '-';
		}
		document.getElementById('tab_pfResult').style.height = (320 + (Math.max(pf_purity_dpp04.length, pf_purity_dpp4.length) - 1) * 20).toString() + 'px';
	}

	if (Array.isArray(result_fission_IFN_dpp4) && result_fission_IFN_dpp4.length===0 && Array.isArray(result_fission_IFN_dpp04) && result_fission_IFN_dpp04.length===0){
		flag += 1;
	}else{
		document.getElementById('tab_fissionResult_IFN').style.display = 'block';
		if (Array.isArray(result_fission_IFN_dpp4) && result_fission_IFN_dpp4.length > 0){
			document.getElementById('tab_fissionResult_IFN').rows[1].cells[1].innerHTML = result_fission_IFN_dpp4[0].toExponential(3).toString() + ' pps';
			let fission_IFN_charge_dpp4_info = result_fission_IFN_dpp4[1].split(',');
			var fission_IFN_charge_dpp4_line = [];
			for (let item of fission_IFN_charge_dpp4_info){
				fission_IFN_charge_dpp4_line.push(item.split(':')[0]+'+: ' + Number(item.split(':')[1]).toExponential(3).toString() + ' pps');
			}
			document.getElementById('tab_fissionResult_IFN').rows[2].cells[1].innerHTML = fission_IFN_charge_dpp4_line.join('<br/>');
			let fission_IFN_purity_dpp4 = (result_fission_IFN_dpp4[2]*100).toFixed(3)
			if (fission_IFN_purity_dpp4 < 0.001){
				fission_IFN_purity_dpp4 = (result_fission_IFN_dpp4[2]*100).toExponential(3)
			}
			document.getElementById('tab_fissionResult_IFN').rows[3].cells[1].innerHTML = fission_IFN_purity_dpp4.toString() + ' %';
			document.getElementById('tab_fissionResult_IFN').rows[4].cells[1].innerHTML = result_fission_IFN_dpp4[3];
			document.getElementById('tab_fissionResult_IFN').rows[5].cells[1].innerHTML = result_fission_IFN_dpp4[4].toString() + ' MeV/u' ;
			document.getElementById('tab_fissionResult_IFN').rows[6].cells[1].innerHTML = result_fission_IFN_dpp4[5].toExponential(3).toString() + ' pps' ;
			document.getElementById('tab_fissionResult_IFN').rows[7].cells[1].innerHTML = result_fission_IFN_dpp4[6] + ' Tm';
			document.getElementById('tab_fissionResult_IFN').rows[8].cells[1].innerHTML = result_fission_IFN_dpp4[7];
			document.getElementById('tab_fissionResult_IFN').rows[9].cells[1].innerHTML = '<span>' + result_fission_IFN_dpp4[8].toString() + ' mg/cm<sup>2</sup></span>';
			//console.log(result_fission_IFN[9]);
			document.getElementById('a_fission_IFN_dpp4').href = '/files/fission/IFN/' + result_fission_IFN_dpp4[9] + '_Test_auto_Run.lpp';

		}else{
			document.getElementById('tab_fissionResult_IFN').rows[1].cells[1].innerHTML = '-'; 
			document.getElementById('tab_fissionResult_IFN').rows[2].cells[1].innerHTML = '-';
			document.getElementById('tab_fissionResult_IFN').rows[3].cells[1].innerHTML = '-'; 
			document.getElementById('tab_fissionResult_IFN').rows[4].cells[1].innerHTML = '-'; 
			document.getElementById('tab_fissionResult_IFN').rows[5].cells[1].innerHTML = '-'; 
			document.getElementById('tab_fissionResult_IFN').rows[6].cells[1].innerHTML = '-'; 
			document.getElementById('tab_fissionResult_IFN').rows[7].cells[1].innerHTML = '-'; 
			document.getElementById('tab_fissionResult_IFN').rows[8].cells[1].innerHTML = '-'; 
			document.getElementById('tab_fissionResult_IFN').rows[9].cells[1].innerHTML = '-'; 
		}
		if (Array.isArray(result_fission_IFN_dpp04) && result_fission_IFN_dpp04.length > 0){
			document.getElementById('tab_fissionResult_IFN').rows[1].cells[2].innerHTML = result_fission_IFN_dpp04[0].toExponential(3).toString() + ' pps';
			let fission_IFN_charge_dpp04_info = result_fission_IFN_dpp04[1].split(',');
			var fission_IFN_charge_dpp04_line = [];
			for (let item of fission_IFN_charge_dpp04_info){
				fission_IFN_charge_dpp04_line.push(item.split(':')[0]+'+: ' + Number(item.split(':')[1]).toExponential(3).toString() + ' pps');
			}
			document.getElementById('tab_fissionResult_IFN').rows[2].cells[1].innerHTML = fission_IFN_charge_dpp04_line.join('<br/>');
			let fission_IFN_purity_dpp04 = (result_fission_IFN_dpp04[2]*100).toFixed(3)
			if (fission_IFN_purity_dpp04 < 0.001){
				fission_IFN_purity_dpp04 = (result_fission_IFN_dpp04[2]*100).toExponential(3)
			}
			document.getElementById('tab_fissionResult_IFN').rows[3].cells[2].innerHTML = fission_IFN_purity_dpp04.toString() + ' %';
			document.getElementById('tab_fissionResult_IFN').rows[4].cells[2].innerHTML = result_fission_IFN_dpp04[3];
			document.getElementById('tab_fissionResult_IFN').rows[5].cells[2].innerHTML = result_fission_IFN_dpp04[4].toString() + ' MeV/u' ;
			document.getElementById('tab_fissionResult_IFN').rows[6].cells[2].innerHTML = result_fission_IFN_dpp04[5].toExponential(3).toString() + ' pps' ;
			document.getElementById('tab_fissionResult_IFN').rows[7].cells[2].innerHTML = result_fission_IFN_dpp04[6] + ' Tm';
			document.getElementById('tab_fissionResult_IFN').rows[8].cells[2].innerHTML = result_fission_IFN_dpp04[7];
			document.getElementById('tab_fissionResult_IFN').rows[9].cells[2].innerHTML = '<span>' + result_fission_IFN_dpp04[8].toString() + ' mg/cm<sup>2</sup></span>';
			//console.log(result_fission_IFN[9]);
			document.getElementById('a_fission_IFN_dpp04').href = '/files/fission/IFN/' + result_fission_IFN_dpp04[9] + '_Test_auto_Run.lpp';

		}else{
			document.getElementById('tab_fissionResult_IFN').rows[1].cells[2].innerHTML = '-'; 
			document.getElementById('tab_fissionResult_IFN').rows[2].cells[2].innerHTML = '-';
			document.getElementById('tab_fissionResult_IFN').rows[3].cells[2].innerHTML = '-'; 
			document.getElementById('tab_fissionResult_IFN').rows[4].cells[2].innerHTML = '-'; 
			document.getElementById('tab_fissionResult_IFN').rows[5].cells[2].innerHTML = '-'; 
			document.getElementById('tab_fissionResult_IFN').rows[6].cells[2].innerHTML = '-'; 
			document.getElementById('tab_fissionResult_IFN').rows[7].cells[2].innerHTML = '-'; 
			document.getElementById('tab_fissionResult_IFN').rows[8].cells[2].innerHTML = '-'; 
			document.getElementById('tab_fissionResult_IFN').rows[9].cells[2].innerHTML = '-'; 
		}
		document.getElementById('tab_fissionResult_IFN').style.height = (320 + (Math.max(fission_IFN_charge_dpp4_line.length, fission_IFN_charge_dpp04_line) - 1) * 20).toString() + 'px';
	}
	
		
	if (Array.isArray(result_fission_IMP) && result_fission_IMP.length > 0){
		document.getElementById('tab_fissionResult_IMP').style.display = 'block';
		document.getElementById('tab_fissionResult_IMP').rows[0].cells[1].innerHTML = result_fission_IMP[0].toExponential(3).toString() + ' pps';
		let fission_IMP_charge_info = result_fission_IMP[1].split(',');
		var fission_IMP_charge_line = [];
		for (let item of fission_IMP_charge_info){
			fission_IMP_charge_line.push(item.split(':')[0]+'+: ' + Number(item.split(':')[1]).toExponential(3).toString() + ' pps');
		}
		document.getElementById('tab_fissionResult_IMP').rows[1].cells[1].innerHTML = fission_IMP_charge_line.join('<br/>');
		document.getElementById('tab_fissionResult_IMP').style.height = (320 + (fission_IMP_charge_line.length - 1) * 20).toString() + 'px';
		let fission_IMP_purity = (result_fission_IMP[2]*100).toFixed(3)
		if (fission_IMP_purity < 0.001){
			fission_IMP_purity = (result_fission_IMP[2]*100).toExponential(3)
		}
		document.getElementById('tab_fissionResult_IMP').rows[2].cells[1].innerHTML = fission_IMP_purity.toString() + ' %';
		document.getElementById('tab_fissionResult_IMP').rows[3].cells[1].innerHTML = result_fission_IMP[3];
		document.getElementById('tab_fissionResult_IMP').rows[4].cells[1].innerHTML = result_fission_IMP[4].toString() + ' MeV/u' ;
		document.getElementById('tab_fissionResult_IMP').rows[5].cells[1].innerHTML = result_fission_IMP[5].toExponential(3).toString() + ' pps' ;
		document.getElementById('tab_fissionResult_IMP').rows[6].cells[1].innerHTML = result_fission_IMP[6] + ' Tm';
		document.getElementById('tab_fissionResult_IMP').rows[7].cells[1].innerHTML = result_fission_IMP[7];
		document.getElementById('tab_fissionResult_IMP').rows[8].cells[1].innerHTML = '<span>' + result_fission_IMP[8].toString() + ' mg/cm<sup>2</sup></span>';
		//console.log(result_fission[9]);
		document.getElementById('a_fission_IMP').href = '/files/fission/IMP/' + result_fission_IMP[9] + '_Test_auto_Run.lpp'
	}else{
		flag += 1;
	}

		
	if (flag == 3){
		document.getElementById('p_error1').style.display = 'block';	
	}else if (flag == 2){
		document.getElementById('div_result').style.height = (640 + (Math.max(pf_charge_dpp04_line.length, pf_charge_dpp4_line.length) - 1)*20).toString() + 'px';
	}else{
		document.getElementById('div_result').style.height = (1280 + (Math.max(fission_IFN_charge_dpp04_line.length, fission_IFN_charge_dpp4_line.length) + fission_IMP_charge_line.length + Math.max(pf_charge_dpp04_line.length, pf_charge_dpp4_line.length) - 2)*20).toString() + 'px';
	}

	// hidden .lpp download except for the default ion
	if (flag != 3){
		if (document.getElementById('atomic_number').value != 50 || document.getElementById('mass_number').value != 111){
		document.getElementById('p_warning_file_1').style.display = 'block';
		document.getElementById('tr_pf_file').style.display = 'none';
		document.getElementById('tr_fission_IFN_file').style.display = 'none';
		document.getElementById('tr_fission_IMP_file').style.display = 'none';
		}else{
			document.getElementById('p_warning_file_0').style.display = 'block';
		}
	}
}

function estimate_init(){
	document.getElementById('p_error0').style.display = 'none';
	document.getElementById('p_error1').style.display = 'none';
	document.getElementById('tab_nuclei').style.display = 'none';
	document.getElementById('tab_pfResult').style.display = 'none';
	document.getElementById('tab_fissionResult_IMP').style.display = 'none';
	document.getElementById('tab_fissionResult_IFN').style.display = 'none';
	document.getElementById('p_warning_file_0').style.display = 'none';
	document.getElementById('p_warning_file_1').style.display = 'none';
	document.getElementById('div_result').style.display = 'none';
	document.getElementById('tr_pf_file').style.display = 'table-row';
	document.getElementById('tr_fission_IFN_file').style.display = 'table-row';
	document.getElementById('tr_fission_IMP_file').style.display = 'table-row';
}

const button_estimate = document.getElementById('estimate');


button_estimate.addEventListener('click', function() {
	estimate_init();
	checkNuclei();

});
