async function checkNuclei(){
	const [SQL, buf] = await Promise.all([
		initSqlJs({locateFile: file=> `/dist/${file}`}),
		fetch("/dist/nuclei_data.sqlite").then(res => res.arrayBuffer())
		// nuclei_data from NUBASE2020
	]);
	const db = new SQL.Database(new Uint8Array(buf));
	let stmt = db.prepare("SELECT ElEMENT, HALFLIFE FROM TOTALNUCLEIDATA WHERE Z=$zval AND A=$aval");
	let result = stmt.get({'$zval': document.getElementById('atomic_number').value, '$aval': document.getElementById('mass_number').value});
	//console.log(result);
	if (Array.isArray(result) && result.length===0){
		document.getElementById('div_result').style.display = 'block';	
		document.getElementById('p_error0').style.display = 'block';	
	}else{
		document.getElementById('div_result').style.display = 'block';	
		document.getElementById('tab_nuclei').style.display = 'block';	
		document.getElementById('tab_nuclei').rows[0].cells[1].innerHTML = document.getElementById('mass_number').value;	
		document.getElementById('tab_nuclei').rows[1].cells[1].innerHTML = document.getElementById('atomic_number').value;	
		document.getElementById('tab_nuclei').rows[2].cells[1].innerHTML = result[0];	
		document.getElementById('tab_nuclei').rows[3].cells[1].innerHTML = result[1];	
		stmt.free();
		stmt = db.prepare("SELECT YIELD, PURE, BEAM, ENERGY, THICKNESS, FILENAME FROM FISSIONDATA WHERE A=$aval AND ELEMENT=$eleval");
		let result_fission = stmt.get({'$aval': document.getElementById('mass_number').value, '$eleval': result[0]});
		//console.log(result_fission);
		stmt.free();
		stmt = db.prepare("SELECT YIELD, PURE, BEAM, ENERGY, THICKNESS, FILENAME FROM PFDATA WHERE A=$aval AND ELEMENT=$eleval");
		let result_pf = stmt.get({'$aval': document.getElementById('mass_number').value, '$eleval': result[0]});
		//console.log(result_pf);
		let flag = 0;
		if (Array.isArray(result_fission) && result_fission.length > 0){
			document.getElementById('tab_fissionResult').style.display = 'block';
			document.getElementById('tab_fissionResult').rows[0].cells[1].innerHTML = result_fission[0].toExponential(3).toString() + ' pps';
			let temp_purity = (result_fission[1]*100).toFixed(3)
			if (temp_purity < 0.001){
				temp_purity = (result_fission[1]*100).toExponential(3)
			}
			document.getElementById('tab_fissionResult').rows[1].cells[1].innerHTML = temp_purity.toString() + ' %';
			document.getElementById('tab_fissionResult').rows[2].cells[1].innerHTML = result_fission[2];
			document.getElementById('tab_fissionResult').rows[3].cells[1].innerHTML = result_fission[3].toString() + ' MeV/u' ;
			document.getElementById('tab_fissionResult').rows[4].cells[1].innerHTML = '<span>' + result_fission[4].toString() + ' mg/cm<sup>2</sup></span>';
		}else{
			flag += 1;
		}
		if (Array.isArray(result_pf) && result_pf.length > 0){
			document.getElementById('tab_pfResult').style.display = 'block';
			document.getElementById('tab_pfResult').rows[0].cells[1].innerHTML = result_pf[0].toExponential(3).toString() + ' pps';
			temp_purity = (result_pf[1]*100).toFixed(3)
			if (temp_purity < 0.001){
				temp_purity = (result_pf[1]*100).toExponential(3)
			}
			document.getElementById('tab_pfResult').rows[1].cells[1].innerHTML = temp_purity.toString() + ' %';
			document.getElementById('tab_pfResult').rows[2].cells[1].innerHTML = result_pf[2].match(/\d{2,3}[A-Za-z]{1,2}/g);
			document.getElementById('tab_pfResult').rows[3].cells[1].innerHTML = result_pf[3].toString() + ' MeV/u' ;
			document.getElementById('tab_pfResult').rows[4].cells[1].innerHTML = '<span>' + result_pf[4].toString() + ' mg/cm<sup>2</sup></span>';
		}else{
			flag += 1;
		}
		if (flag == 2){
			document.getElementById('p_error1').style.display = 'block';	
		}

	}
}

function estimate_init(){
	document.getElementById('p_error0').style.display = 'none';
	document.getElementById('p_error1').style.display = 'none';
	document.getElementById('tab_nuclei').style.display = 'none';
	document.getElementById('tab_pfResult').style.display = 'none';
	document.getElementById('tab_fissionResult').style.display = 'none';
	document.getElementById('p_file').style.display = 'none';
	document.getElementById('div_result').style.display = 'none';
}

const button_estimate = document.getElementById('estimate');


button_estimate.addEventListener('click', function() {
	estimate_init();
	checkNuclei();

});
