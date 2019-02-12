import java.io.BufferedReader;
import java.io.FileReader;
import java.math.BigInteger;
import java.math.BigDecimal;


public class ElGamal {

  public static String decodeMessage(BigInteger m) {
    return new String(m.toByteArray());
  }  

  public static void main(String[] arg) {
    String filename = "input_elgamal.txt";
    try {
      BufferedReader br = new BufferedReader(new FileReader(filename));
      BigInteger p = new BigInteger(br.readLine().split("=")[1]); // GROUPSIZE
      BigInteger g = new BigInteger(br.readLine().split("=")[1]); // GENERATOR
      BigInteger y = new BigInteger(br.readLine().split("=")[1]); // PUBLIC KEY OF THE RECIEVER
      String line = br.readLine().split("=")[1];
      String date = line.split(" ")[0];
      String time = line.split(" ")[1];
      int year  = Integer.parseInt(date.split("-")[0]);
      int month = Integer.parseInt(date.split("-")[1]);
      int day   = Integer.parseInt(date.split("-")[2]);
      int hour   = Integer.parseInt(time.split(":")[0]);
      int minute = Integer.parseInt(time.split(":")[1]);
      int second = Integer.parseInt(time.split(":")[2]);
      BigInteger c1 = new BigInteger(br.readLine().split("=")[1]); // ELGAMAL ENCRYPTION
      BigInteger c2 = new BigInteger(br.readLine().split("=")[1]); // ELGAMAL ENCRYPTION
      br.close();
      BigInteger m = recoverSecret(p, g, y, year, month, day, hour, minute,
          second, c1, c2);
      System.out.println("Recovered message: " + m);
      System.out.println("Decoded text: " + decodeMessage(m));
    } catch (Exception err) {
      System.err.println("Error handling file.");
      err.printStackTrace();
      System.exit(1);
    }
  }
  
  public static BigInteger recoverSecret(BigInteger p, BigInteger g,
      BigInteger y, int year, int month, int day, int hour, int minute,
      int second, BigInteger c1, BigInteger c2) {
//-----------------------------------------------------------------------------------------------------------------
// DECRYPTING
// c1 =  g ^ r (COMPLETED)
// c2 = m * h^r, where h = g ^ exp mod p => exp = 	
//-----------------------------------------------------------------------------------------------------------------
    BigDecimal decimalvalue = BigDecimal.valueOf((year * Math.pow(10,10) )).add(BigDecimal.valueOf((month * Math.pow(10,8) ))).add( 
                              BigDecimal.valueOf((day * Math.pow(10,6) ))).add(BigDecimal.valueOf((hour * Math.pow(10,4) ))).add(
                              BigDecimal.valueOf((minute * Math.pow(10,2) )).add(BigDecimal.valueOf((second))));
    BigInteger r_without_ms = decimalvalue.toBigInteger();
	//--- calculating the missing part of the randomnumber, ms ---//
    BigInteger ms = null;
    BigInteger r = null;
    BigInteger gen_c1 = null;

    System.out.println("Finding ms...");
    for(int i = 0; i < 1000; i++) {
		ms = BigInteger.valueOf((int) i);
		r = r_without_ms.add(ms);
		gen_c1 = g.modPow(r, p);
	    	if(c1.equals(gen_c1)) {
	    		System.out.println("It's a match!");
	    		System.out.println("milisecond is " + ms);
	    		System.out.println("The complete random number is " + r);
	    		break;
	    	}
    }
    //--- , msg = C1 * modInv(public_key^r) mod p ---//
    BigInteger msg = null;
    BigInteger t = y.modPow(r,p);
    BigInteger neg_num = new BigInteger("-1");
    BigInteger inv = t.modPow(neg_num,p);
    msg = c2.multiply(inv).mod(p);
    return msg;
  }
  
}