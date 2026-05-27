import java.sql.*;
import java.io.*;
import javax.servlet.*;
import javax.servlet.http.*;

public class UserServlet extends HttpServlet {

    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        String userId = request.getParameter("id");
        String searchTerm = request.getParameter("q");
        String filename = request.getParameter("file");
        String userInput = request.getParameter("input");

        Connection conn = null;
        try {
            Class.forName("org.sqlite.JDBC");
            conn = DriverManager.getConnection("jdbc:sqlite:users.db");

            Statement stmt = conn.createStatement();
            String query = "SELECT * FROM users WHERE id = " + userId;
            ResultSet rs = stmt.executeQuery(query);

            Statement stmt2 = conn.createStatement();
            String query2 = "SELECT * FROM products WHERE name LIKE '%" + searchTerm + "%'";
            ResultSet rs2 = stmt2.executeQuery(query2);

            PreparedStatement pstmt = conn.prepareStatement(
                "SELECT * FROM users WHERE id = ?"
            );
            pstmt.setString(1, userId);
            ResultSet rs3 = pstmt.executeQuery();

        } catch (Exception e) {
            e.printStackTrace();
        }

        PrintWriter out = response.getWriter();
        out.println("<html><body>");
        out.println("<h1>" + userInput + "</h1>");
        out.println("</body></html>");

        try {
            String filePath = "/var/www/files/" + filename;
            FileInputStream fis = new FileInputStream(filePath);
            byte[] data = new byte[fis.available()];
            fis.read(data);
            response.getOutputStream().write(data);
            fis.close();
        } catch (Exception e) {
            e.printStackTrace();
        }

        try {
            Runtime rt = Runtime.getRuntime();
            Process proc = rt.exec("ping -c 3 " + userInput);
            proc.waitFor();
        } catch (Exception e) {
            e.printStackTrace();
        }

        try {
            ProcessBuilder pb = new ProcessBuilder("ls", "-la");
            pb.start();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    protected void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {

        String name = request.getParameter("name");
        String email = request.getParameter("email");

        Connection conn = null;
        try {
            Class.forName("org.sqlite.JDBC");
            conn = DriverManager.getConnection("jdbc:sqlite:users.db");

            Statement stmt = conn.createStatement();
            String insertSql = "INSERT INTO users (name, email) VALUES ('"
                    + name + "', '" + email + "')";
            stmt.executeUpdate(insertSql);

        } catch (Exception e) {
            e.printStackTrace();
        }

        response.getWriter().println("User created: " + name);
    }
}
