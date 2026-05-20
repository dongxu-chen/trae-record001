package com.econtract.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.TypeReference;
import com.econtract.dto.SignPositionDTO;
import com.econtract.dto.TemplateFieldDTO;
import lombok.extern.slf4j.Slf4j;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.font.PDType0Font;
import org.apache.pdfbox.pdmodel.graphics.image.PDImageXObject;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.IOException;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
public class PdfService {

    @Value("${file.signed-path}")
    private String signedPath;

    @Value("${file.upload-path}")
    private String uploadPath;

    public String fillForm(String templatePath, String formDataJson, String fieldsJson) throws IOException {
        File dir = new File(uploadPath);
        if (!dir.exists()) {
            dir.mkdirs();
        }
        String fileName = UUID.randomUUID().toString().replace("-", "") + ".pdf";
        String outputPath = uploadPath + fileName;

        try (PDDocument document = PDDocument.load(new File(templatePath))) {
            if (formDataJson != null && fieldsJson != null) {
                Map<String, String> formData = JSON.parseObject(formDataJson, new TypeReference<Map<String, String>>() {});
                List<TemplateFieldDTO> fields = JSON.parseArray(fieldsJson, TemplateFieldDTO.class);

                PDType0Font font = PDType0Font.load(document,
                        new File("src/main/resources/fonts/simsun.ttf"), true);

                for (TemplateFieldDTO field : fields) {
                    String value = formData.get(field.getFieldName());
                    if (value != null) {
                        PDPage page = document.getPage(0);
                        try (PDPageContentStream contentStream = new PDPageContentStream(
                                document, page, PDPageContentStream.AppendMode.APPEND, true, true)) {
                            contentStream.beginText();
                            contentStream.setFont(font, 12);
                            contentStream.newLineAtOffset(100, 700 - fields.indexOf(field) * 30);
                            contentStream.showText(value);
                            contentStream.endText();
                        }
                    }
                }
            }
            document.save(outputPath);
        }
        return outputPath;
    }

    public String addSignature(String pdfPath, String signatureImage, String signPositionJson) throws IOException {
        File dir = new File(signedPath);
        if (!dir.exists()) {
            dir.mkdirs();
        }
        String fileName = UUID.randomUUID().toString().replace("-", "") + ".pdf";
        String outputPath = signedPath + fileName;

        try (PDDocument document = PDDocument.load(new File(pdfPath))) {
            SignPositionDTO position = JSON.parseObject(signPositionJson, SignPositionDTO.class);
            if (position == null) {
                position = new SignPositionDTO();
                position.setPageNum(1);
                position.setX(400f);
                position.setY(100f);
                position.setWidth(150f);
                position.setHeight(80f);
            }

            PDPage page = document.getPage(position.getPageNum() - 1);
            BufferedImage image = base64ToImage(signatureImage);
            PDImageXObject pdImage = PDImageXObject.createFromImage(document, image, fileName);

            try (PDPageContentStream contentStream = new PDPageContentStream(
                    document, page, PDPageContentStream.AppendMode.APPEND, true, true)) {
                contentStream.drawImage(pdImage, position.getX(), position.getY(),
                        position.getWidth(), position.getHeight());
            }
            document.save(outputPath);
        }
        return outputPath;
    }

    private BufferedImage base64ToImage(String base64) throws IOException {
        if (base64.contains(",")) {
            base64 = base64.split(",")[1];
        }
        byte[] bytes = Base64.getDecoder().decode(base64);
        try (ByteArrayInputStream bis = new ByteArrayInputStream(bytes)) {
            return ImageIO.read(bis);
        }
    }

    public byte[] getFileBytes(String filePath) throws IOException {
        File file = new File(filePath);
        try (java.io.FileInputStream fis = new java.io.FileInputStream(file)) {
            byte[] bytes = new byte[(int) file.length()];
            fis.read(bytes);
            return bytes;
        }
    }
}
