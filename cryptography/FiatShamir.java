import java.io.BufferedReader;
import java.io.FileReader;
import java.math.BigInteger;
//199412245327
public class FiatShamir {

	public static class ProtocolRun {
		public final BigInteger R;
		public final int c;
		public final BigInteger s;

		public ProtocolRun(BigInteger R, int c, BigInteger s) {
			this.R = R; // random value sent to verifier from prover, we now that there are two identical
			this.c = c; // challenge recieved by the prover, either 0 or 1
			this.s = s; // proof that is sent back to verifier, a and a'
		}
	}

	public static void main(String[] args) {
		String filename = "input.txt"; 
		BigInteger N = BigInteger.ZERO; // N = pq, which is public known
		BigInteger X = BigInteger.ZERO; // public key
		ProtocolRun[] runs = new ProtocolRun[10]; // array of 10 ProtocolsRun objects 
		try {
			BufferedReader br = new BufferedReader(new FileReader(filename));
			N = new BigInteger(br.readLine().split("=")[1]); // modulo
			X = new BigInteger(br.readLine().split("=")[1]); // public key
			for (int i = 0; i < 10; i++) {
				String line = br.readLine();
				String[] elem = line.split(",");
				runs[i] = new ProtocolRun(
						new BigInteger(elem[0].split("=")[1]),
						Integer.parseInt(elem[1].split("=")[1]),
						new BigInteger(elem[2].split("=")[1]));
			}
			br.close();
		} catch (Exception err) {
			System.err.println("Error handling file.");
			err.printStackTrace();
			System.exit(1);
		}
		BigInteger m = recoverSecret(N, X, runs);
		System.out.println("Recovered message: " + m);
		System.out.println("Decoded text: " + decodeMessage(m));
	}

	public static String decodeMessage(BigInteger m) {
		return new String(m.toByteArray());
	}

	/**
	 * Recovers the secret used in this collection of Fiat-Shamir protocol runs.
	 * 
	 * @param N
	 *            The modulus
	 * @param X
	 *            The public component
	 * @param runs
	 *            Ten runs of the protocol.
	 * @return
	 */
	private static BigInteger recoverSecret(BigInteger N, BigInteger X,
			ProtocolRun[] runs) {
		// TODO. Recover the secret value x such that x^2 = X (mod N).
		for(ProtocolRun p : runs) {
			for(ProtocolRun q : runs) {
				if(p.R.equals(q.R)) { // Comparing R for each run of the protocol
					if(p.c == 0) { // we want to know when c = 0, since a = R * S^0 mod n => a = R * 1 mod n
						BigInteger inv = p.s.modInverse(N); // a = R * S^0 mod N, a^-1 = 1/R * 1 mod N 
						BigInteger secret = inv.multiply(q.s).mod(N); // a^-1 * a' = 1/R * 1 mod N * R * S^1 mod N => S mod N
						if(X.equals(secret.pow(2).mod(N))) //X = secret^2
							return secret;
					}
				}
			}
		}
		return BigInteger.ZERO;
	}
}