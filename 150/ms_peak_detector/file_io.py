import numpy as np
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict, Optional
import os
from datetime import datetime


class MzMLWriter:
    def __init__(self):
        self.ms_level_names = {1: "MS1 spectrum", 2: "MSn spectrum"}
    
    def write_mzml(self, spectra: List[Dict], output_path: str,
                   instrument: str = "Unknown",
                   sample_name: str = "Sample_1") -> None:
        root = ET.Element("mzML")
        root.set("xmlns", "http://psi.hupo.org/ms/mzml")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        root.set("xsi:schemaLocation", "http://psi.hupo.org/ms/mzml http://psidev.info/files/ms/mzML/xsd/mzML1.1.0.xsd")
        root.set("version", "1.1.0")
        
        self._add_cv_list(root)
        self._add_file_description(root, instrument)
        self._add_sample_list(root, sample_name)
        self._add_software_list(root)
        self._add_scan_settings_list(root)
        self._add_instrument_configuration_list(root, instrument)
        self._add_data_processing_list(root)
        self._add_spectrum_list(root, spectra)
        
        xml_str = minidom.parseString(ET.tostring(root, encoding="unicode")).toprettyxml(indent="  ")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(xml_str)
    
    def _add_cv_list(self, parent: ET.Element) -> None:
        cv_list = ET.SubElement(parent, "cvList")
        
        cv1 = ET.SubElement(cv_list, "cv")
        cv1.set("id", "MS")
        cv1.set("fullName", "PSI Mass Spectrometry Ontology")
        cv1.set("version", "4.1.0")
        cv1.set("URI", "https://github.com/HUPO-PSI/psi-ms-CV/releases/download/v4.1.0/psi-ms.obo")
        
        cv2 = ET.SubElement(cv_list, "cv")
        cv2.set("id", "UO")
        cv2.set("fullName", "Unit Ontology")
        cv2.set("version", "0.9.15")
        cv2.set("URI", "https://raw.githubusercontent.com/bio-ontology-research-group/unit-ontology/master/unit.obo")
    
    def _add_file_description(self, parent: ET.Element, instrument: str) -> None:
        file_desc = ET.SubElement(parent, "fileDescription")
        
        file_content = ET.SubElement(file_desc, "fileContent")
        cv_param1 = ET.SubElement(file_content, "cvParam")
        cv_param1.set("cvRef", "MS")
        cv_param1.set("accession", "MS:1000579")
        cv_param1.set("name", "MS1 spectrum")
        cv_param2 = ET.SubElement(file_content, "cvParam")
        cv_param2.set("cvRef", "MS")
        cv_param2.set("accession", "MS:1000580")
        cv_param2.set("name", "MSn spectrum")
        
        source_file_list = ET.SubElement(file_desc, "sourceFileList")
        source_file = ET.SubElement(source_file_list, "sourceFile")
        source_file.set("id", "SF1")
        source_file.set("name", "generated_data")
        source_file.set("location", "file:///generated")
        
        contact = ET.SubElement(file_desc, "contact")
        contact.set("id", "C1")
    
    def _add_sample_list(self, parent: ET.Element, sample_name: str) -> None:
        sample_list = ET.SubElement(parent, "sampleList")
        sample = ET.SubElement(sample_list, "sample")
        sample.set("id", "S1")
        sample.set("name", sample_name)
    
    def _add_software_list(self, parent: ET.Element) -> None:
        software_list = ET.SubElement(parent, "softwareList")
        software = ET.SubElement(software_list, "software")
        software.set("id", "SW1")
        software.set("version", "1.0")
        cv_param = ET.SubElement(software, "cvParam")
        cv_param.set("cvRef", "MS")
        cv_param.set("accession", "MS:1000799")
        cv_param.set("name", "custom unreleased software tool")
    
    def _add_scan_settings_list(self, parent: ET.Element) -> None:
        scan_settings_list = ET.SubElement(parent, "scanSettingsList")
        scan_settings = ET.SubElement(scan_settings_list, "scanSettings")
        scan_settings.set("id", "SS1")
    
    def _add_instrument_configuration_list(self, parent: ET.Element, instrument: str) -> None:
        config_list = ET.SubElement(parent, "instrumentConfigurationList")
        config = ET.SubElement(config_list, "instrumentConfiguration")
        config.set("id", "IC1")
        
        component_list = ET.SubElement(config, "componentList")
        
        source = ET.SubElement(component_list, "source")
        source.set("order", "1")
        cv_param = ET.SubElement(source, "cvParam")
        cv_param.set("cvRef", "MS")
        cv_param.set("accession", "MS:1000008")
        cv_param.set("name", "electrospray ionization")
        
        analyzer = ET.SubElement(component_list, "analyzer")
        analyzer.set("order", "2")
        cv_param = ET.SubElement(analyzer, "cvParam")
        cv_param.set("cvRef", "MS")
        cv_param.set("accession", "MS:1000084")
        cv_param.set("name", "orbitrap")
        
        detector = ET.SubElement(component_list, "detector")
        detector.set("order", "3")
        cv_param = ET.SubElement(detector, "cvParam")
        cv_param.set("cvRef", "MS")
        cv_param.set("accession", "MS:1000253")
        cv_param.set("name", "electron multiplier")
    
    def _add_data_processing_list(self, parent: ET.Element) -> None:
        dp_list = ET.SubElement(parent, "dataProcessingList")
        dp = ET.SubElement(dp_list, "dataProcessing")
        dp.set("id", "DP1")
        
        method = ET.SubElement(dp, "processingMethod")
        method.set("order", "1")
        method.set("softwareRef", "SW1")
        
        cv_param1 = ET.SubElement(method, "cvParam")
        cv_param1.set("cvRef", "MS")
        cv_param1.set("accession", "MS:1000544")
        cv_param1.set("name", "Conversion to mzML")
        
        cv_param2 = ET.SubElement(method, "cvParam")
        cv_param2.set("cvRef", "MS")
        cv_param2.set("accession", "MS:1000035")
        cv_param2.set("name", "peak picking")
    
    def _add_spectrum_list(self, parent: ET.Element, spectra: List[Dict]) -> None:
        spectrum_list = ET.SubElement(parent, "spectrumList")
        spectrum_list.set("count", str(len(spectra)))
        spectrum_list.set("defaultDataProcessingRef", "DP1")
        
        for i, spectrum in enumerate(spectra):
            self._add_spectrum(spectrum_list, spectrum, i + 1)
    
    def _add_spectrum(self, parent: ET.Element, spectrum: Dict, index: int) -> None:
        mz = spectrum.get("mz", np.array([]))
        intensity = spectrum.get("intensity", np.array([]))
        ms_level = spectrum.get("ms_level", 1)
        
        spec = ET.SubElement(parent, "spectrum")
        spec.set("id", f"index={index}")
        spec.set("index", str(index - 1))
        spec.set("defaultArrayLength", str(len(mz)))
        
 cv = ET.SubElement(parent, "cvParam")
        cv.set("cvRef", "MS")
 cv.set("accession", "MS:1000511")
        cv.set("name", "ms level")
        cv.set("value", str(ms_level))
        
        cv = ET.SubElement(parent, "cvParam")
        cv.set("cvRef", "MS")
        cv.set("accession", "MS:1000579")
        cv.set("name", "MS1 spectrum")
        
        binary_data_array_list = ET.SubElement(parent, "binaryDataArrayList")
        
        mz_array = ET.SubElement(parent, "binaryDataArray")
        cv = ET.SubElement(mz_array, "cvParam")
        cv.set("cvRef", "MS")
        cv.set("accession", "MS:1000514")
        cv.set("name", "m/z array")
        cv.set("unitRef", "MS")
        cv.set("unitAccession", "MS:1000040")
        cv.set("unitName", "m/z")
        
        binary = ET.SubElement(mz_array, "binary")
        
        intensity_array = ET.SubElement(parent, "binaryDataArray")
        cv = ET.SubElement(intensity_array, "cvParam")
        cv.set("cvRef", "MS")
        cv.set("accession", "MS:1000515")
        cv.set("name", "intensity array")
        cv.set("unitRef", "MS")
        cv.set("unitAccession", "MS:1000131")
        cv.set("unitName", "number of counts")
        
        binary = ET.SubElement(intensity_array, "binary")


class MzTabWriter:
    def __init__(self):
        pass
    
    def write_mztab(self, data: Dict, output_path: str,
                     mode: str = "summary") -> None:
        
        lines = []
        
        lines.append("MTD\tmzTab-version\t1.0.0")
        lines.append(f"MTD\tmzTab-mode\t{mode}")
        lines.append("MTD\tmzTab-type\tQuantification")
        lines.append(f"MTD\tdescription\tGenerated mass spectrometry data")
        lines.append(f"MTD\tsoftware\t[MS, MS:1000799, Custom Software, 1.0]")
        
        if "peptide_quantitation" in data:
            lines.append("\nPEP\tPEP_SEQ\tPEP_ACCESSION\tPEP_UNIQUE")
            
            for i, (peptide, quant) in enumerate(data["peptide_quantitation"].items()):
                seq = peptide
                accession = f"P{i:06d}"
                unique = "1"
                line = f"PEP\t{seq}\t{accession}\t{unique}"
                
                for channel, value in quant.get("mean", {}).items():
                    line += f"\t{value:.4f}"
                
                lines.append(line)
        
        if "protein_quantitation" in data:
            lines.append("\nPRT\tPRT_ACCESSION\tPRT_DESCRIPTION")
            
            for i, (protein, quant) in enumerate(data["protein_quantitation"].items()):
                accession = protein
                description = f"Protein {accession}"
                line = f"PRT\t{accession}\t{description}"
                
                for channel, value in quant.get("mean", {}).items():
                    line += f"\t{value:.4f}"
                
                lines.append(line)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))


class SimpleFileWriter:
    def __init__(self):
        self.mzml_writer = MzMLWriter()
        self.mztab_writer = MzTabWriter()
    
    def write_peaks_csv(self, peaks: List[Dict], output_path: str) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("mz,intensity,peak_id,charge,score\n")
            for i, peak in enumerate(peaks):
                mz = peak.get("mz", 0.0)
                intensity = peak.get("intensity", 0.0)
                charge = peak.get("charge", 0)
                score = peak.get("score", 0.0)
                f.write(f"{mz:.6f},{intensity:.4f},{i},{charge},{score:.3f}\n")
    
    def write_spectrum_csv(self, mz: np.ndarray, intensity: np.ndarray,
                            output_path: str) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("mz,intensity\n")
            for m, i in zip(mz, intensity):
                f.write(f"{m:.6f},{i:.4f}\n")
    
    def write_quantification_tsv(self, quant_data: Dict[str, Dict],
                                   output_path: str, level: str = "protein") -> None:
        channels = list(list(quant_data.values())[0]["mean"].keys())
        
        with open(output_path, "w", encoding="utf-8") as f:
            header = f"{level}_id\t" + "\t".join(channels)
            f.write(header + "\n")
            
            for identifier, data in quant_data.items():
                values = [f"{data['mean'][ch]:.4f}" for ch in channels]
                line = f"{identifier}\t" + "\t".join(values)
                f.write(line + "\n")
    
    def write_ptm_report(self, ptm_results: List[Dict],
                          output_path: str) -> None:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("modification\tposition\tamino_acid\tdelta_score\tscore_ratio\n")
            for result in ptm_results:
                mod = result.get("modification", {})
                name = mod.get("name", "unknown")
                pos = mod.get("position", -1)
                aa = mod.get("amino_acid", "X")
                delta = result.get("delta_score", 0.0)
                ratio = result.get("score_ratio", 0.0)
                f.write(f"{name}\t{pos}\t{aa}\t{delta:.4f}\t{ratio:.4f}\n")


class ResultExporter:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.writer = SimpleFileWriter()
        self._ensure_output_dir()
    
    def _ensure_output_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def export_all(self, results: Dict, prefix: str = "ms_analysis") -> Dict[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        export_files = {}
        
        if "peak_data" in results:
            peaks_path = os.path.join(self.output_dir, f"{prefix}_peaks_{timestamp}.csv")
            self.writer.write_peaks_csv(results["peak_data"], peaks_path)
            export_files["peaks"] = peaks_path
        
        if "quantification" in results:
            quant_data = results["quantification"]
            if "protein_quantitation" in quant_data:
                prot_path = os.path.join(self.output_dir, f"{prefix}_protein_quant_{timestamp}.tsv")
                self.writer.write_quantification_tsv(
                    quant_data["protein_quantitation"], prot_path, "protein"
                )
                export_files["protein_quant"] = prot_path
            
            if "peptide_quantitation" in quant_data:
                pep_path = os.path.join(self.output_dir, f"{prefix}_peptide_quant_{timestamp}.tsv")
                self.writer.write_quantification_tsv(
                    quant_data["peptide_quantitation"], pep_path, "peptide"
                )
                export_files["peptide_quant"] = pep_path
        
        if "ptm_results" in results:
            ptm_path = os.path.join(self.output_dir, f"{prefix}_ptm_report_{timestamp}.tsv")
            self.writer.write_ptm_report(results["ptm_results"], ptm_path)
            export_files["ptm_report"] = ptm_path
        
        if "mztab_data" in results:
            mztab_path = os.path.join(self.output_dir, f"{prefix}_{timestamp}.mzTab")
            self.writer.mztab_writer.write_mztab(results["mztab_data"], mztab_path)
            export_files["mztab"] = mztab_path
        
        return export_files
