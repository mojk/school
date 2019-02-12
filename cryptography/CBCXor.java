import java.io.BufferedReader;
import java.io.FileReader;
import java.util.*;
import javax.xml.bind.DatatypeConverter;

public class CBCXor {

// ----------------------------------------------------------------------------------------------------------------------------------
// CREATING A OBJECT CALLED BLOCK, WHICH HAS A CIPHERTEXT
// ----------------------------------------------------------------------------------------------------------------------------------
	public static class Block {
		public final byte[] ciphertext;

		public Block(byte[] ciphertext) {
			this.ciphertext = ciphertext;
	}
}

	public static void main(String[] args) {
		String filename = "input_cbc.txt";
		byte[] first_block = null;
		byte[] encrypted = null;
		try {
			BufferedReader br = new BufferedReader(new FileReader(filename));
			first_block = br.readLine().getBytes();
			encrypted = DatatypeConverter.parseHexBinary(br.readLine());
			br.close();
		} catch (Exception err) {
			System.err.println("Error handling file.");
			err.printStackTrace();
			System.exit(1);
		}
		String m = recoverMessage(first_block, encrypted);
		System.out.println("Recovered message: " + m);
	}
	/**
	 * Recover the encrypted message (CBC encrypted with XOR, block size = 12).
	 * 
	 * @param first_block
	 *            We know that this is the value of the first block of plain
	 *            text.
	 * @param encrypted
	 *            The encrypted text, of the form IV | C0 | C1 | ... where each
	 *            block is 12 bytes long.
	 */
	private static String recoverMessage(byte[] first_block, byte[] encrypted) {

		ArrayList<Block> AllBlocks = new ArrayList<Block>();
		byte[] key = new byte[12];

// ----------------------------------------------------------------------------------------------------------------------------------
// INITIALIZING BLOCK OBJECTS
// ----------------------------------------------------------------------------------------------------------------------------------
		
		Block iv = new Block(new byte[12]); AllBlocks.add(iv);
		Block c0 = new Block(new byte[12]); AllBlocks.add(c0); Block c1 = new Block(new byte[12]); AllBlocks.add(c1); 
		Block c2 = new Block(new byte[12]); AllBlocks.add(c2); Block c3 = new Block(new byte[12]); AllBlocks.add(c3);
		Block c4 = new Block(new byte[12]); AllBlocks.add(c4);

// ----------------------------------------------------------------------------------------------------------------------------------
// SPLITTING THE ENCRYPTED MESSAGE INTO 5 BLOCKS EACH CONTAINING 12 BYTES, IV | C0 | C1 | C2 | C3 | C4
// pos : used to set the position in which bytes should be written into each block, 0-11 .. etc
// ----------------------------------------------------------------------------------------------------------------------------------

			int pos = 0;		
			for(Block b : AllBlocks) {
				for(int i = 0; i < encrypted.length; i++) {
					b.ciphertext[i] =  encrypted[pos];
					pos++;
					if(pos % 12 == 0) {
						break;
					}
				}
			}
// ----------------------------------------------------------------------------------------------------------------------------------------
// GENERATING THE KEY, SINCE WE HAVE P0, BY USING XOR-OPERATION BETWEEN THE PLAINTEXT AND THE CIPHERKEY, WE CAN GET THE KEY, P0 + C0 = KEY
// REMOVING IV FROM ALL BLOCKS SINCE WHEN DECRYPTING IT WILL NOT BE NEEDED
// ----------------------------------------------------------------------------------------------------------------------------------------

			for(int i = 0; i < c0.ciphertext.length; i++) {
				key[i] = ( (byte) (iv.ciphertext[i] ^ first_block[i] ^ c0.ciphertext[i]));
			}
			AllBlocks.remove(0);

// ----------------------------------------------------------------------------------------------------------------------------------
// DECRYPTING, USING THE XOR OPERATION BETWEENT THE KEY AND EVERY BLOCK AND STORING IT INTO AN BYTE[]
// write : is used to not overwrite each block content when writing to the recovered message array, 0-11.. etc
// ----------------------------------------------------------------------------------------------------------------------------------

			byte[] recoveredmsg = new byte[AllBlocks.size() * iv.ciphertext.length];
			int write = 0;
			for(int j = 1; j < AllBlocks.size(); j++) {
				for(int i = 0; i < 12; i++) {
					// KEY[0-11] XOR Cj-1[0-11] XOR Cj[0-11]
					recoveredmsg[write] = ((byte) (key[i] ^ AllBlocks.get(j-1).ciphertext[i] ^ AllBlocks.get(j).ciphertext[i] ));
					write++;
					if(write % 12 == 0) {
						break;
					}
			}
		}

		return new String(recoveredmsg);
	}
}
